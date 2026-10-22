<?php

/**
 * FrankenPHP Universal Worker Script
 *
 * Em Worker Mode, a aplicação PHP é inicializada uma única vez na memória
 * e atende requisições subsequentes sem custo de inicialização (cold boot),
 * proporcionando latência ultra-baixa e alta vazão de throughput.
 */

// Impede que warnings normais interrompam o loop do worker
ignore_user_abort(true);

// Limite de requisições por thread para reciclar memória e evitar memory leaks
$maxRequests = (int)($_ENV['MAX_REQUESTS'] ?? 1000);

for ($nbRequests = 0; !$maxRequests || $nbRequests < $maxRequests; ++$nbRequests) {
    $keepRunning = \frankenphp_handle_request(function () {
        $uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
        
        // Roteamento dinâmico dentro de /var/www/html
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

    // Limpa estado global / buffers se necessário
    gc_collect_cycles();

    if (!$keepRunning) {
        break;
    }
}
