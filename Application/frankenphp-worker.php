<?php

/**
 * FrankenPHP Universal Worker Script
 *
 * Em Worker Mode, a aplicacao PHP e inicializada uma unica vez na memoria
 * e atende requisicoes subsequentes sem custo de inicializacao (cold boot),
 * proporcionando latencia ultra-baixa e alta vazao de throughput.
 */

// Impede que warnings normais interrompam o loop do worker
ignore_user_abort(true);

// Limite de requisicoes por thread para reciclar memoria e evitar memory leaks
$maxRequests = (int)($_ENV['MAX_REQUESTS'] ?? 1000);

/**
 * Funcao de deteccao inteligente de ambiente (Local, Homologacao, Producao)
 * Injetada no escopo global de cada requisicao processada pelo Worker.
 */
function detect_app_environment(): string {
    // 1. Prioridade para variavel de ambiente explicita (.env / Docker)
    $envConfig = getenv('APP_ENV') ?: (getenv('ENVIRONMENT') ?: ($_ENV['APP_ENV'] ?? ($_SERVER['APP_ENV'] ?? null)));
    if (!empty($envConfig)) {
        $envMap = [
            'local' => 'Local',
            'dev' => 'Local',
            'development' => 'Local',
            'homolog' => 'Homologacao',
            'homologacao' => 'Homologacao',
            'staging' => 'Homologacao',
            'stage' => 'Homologacao',
            'hml' => 'Homologacao',
            'prod' => 'Producao',
            'production' => 'Producao',
            'producao' => 'Producao'
        ];
        return $envMap[strtolower(trim($envConfig))] ?? ucfirst($envConfig);
    }

    // 2. Deteccao automatica com base no Host / Dominio da requisicao
    $rawHost = $_SERVER['HTTP_X_FORWARDED_HOST'] ?? ($_SERVER['HTTP_HOST'] ?? ($_SERVER['SERVER_NAME'] ?? 'localhost'));
    $httpHost = strtolower(trim(explode(':', $rawHost)[0]));

    // Regras de Dominio:
    // Local: localhost, 127.0.0.1, ::1, *.localhost, *.local, *.test
    if ($httpHost === 'localhost' || $httpHost === '127.0.0.1' || $httpHost === '::1' || str_ends_with($httpHost, '.localhost') || str_ends_with($httpHost, '.local') || str_ends_with($httpHost, '.test')) {
        return 'Local';
    }
    // Homologacao: homologacao.charlescorrea.com.br, staging, hml, dev.*
    if ($httpHost === 'homologacao.charlescorrea.com.br' || str_starts_with($httpHost, 'homologacao.') || str_contains($httpHost, 'homolog') || str_contains($httpHost, 'staging') || str_contains($httpHost, 'hml.')) {
        return 'Homologacao';
    }
    // Producao: charlescorrea.com.br, www.charlescorrea.com.br ou qualquer dominio publico
    if ($httpHost === 'charlescorrea.com.br' || $httpHost === 'www.charlescorrea.com.br') {
        return 'Producao';
    }

    // Fallback: se for IP publico direto, assume Producao; caso contrario, Local
    if (filter_var($httpHost, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
        return 'Producao';
    }
    return 'Local';
}

for ($nbRequests = 0; !$maxRequests || $nbRequests < $maxRequests; ++$nbRequests) {
    $keepRunning = \frankenphp_handle_request(function () {
        // Injeta a variavel $appEnv e $_SERVER['APP_ENV'] para todos os scripts despachados
        global $appEnv;
        $appEnv = detect_app_environment();
        $_SERVER['APP_ENV'] = $appEnv;
        $_ENV['APP_ENV'] = $appEnv;

        $uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
        
        // Roteamento dinamico dentro de /var/www/html
        if ($uri === '/' || $uri === '' || $uri === '/index.php') {
            require __DIR__ . '/index.php';
        } elseif (file_exists(__DIR__ . $uri) && !is_dir(__DIR__ . $uri)) {
            require __DIR__ . $uri;
        } elseif (file_exists(__DIR__ . '/info.php') && strpos($uri, 'info') !== false) {
            require __DIR__ . '/info.php';
        } else {
            http_response_code(404);
            echo "404 Not Found";
        }
    });

    // Limpa estado global / buffers se necessario
    gc_collect_cycles();

    if (!$keepRunning) {
        break;
    }
}