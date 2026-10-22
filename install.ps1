<#
.SYNOPSIS
    Instalador e Gerenciador Interativo do Cluster Docker PHP Enterprise (Windows PowerShell)
    Suporta: Seleção de versão única ativa na porta 80/443 (7.4, 8.2, 8.3, 8.4, 8.5),
    Cluster Completo, Geração e Renovação SSL (mkcert / Let's Encrypt),
    Configuração guiada do arquivo .env, ModSecurity WAF, Antivírus ClamAV e Traefik v2.11.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Instalador Docker PHP Enterprise - Traefik Gateway :80/:443"

$root = $PSScriptRoot
Set-Location $root

function Show-Header {
    Clear-Host
    Write-Host "==========================================================================" -ForegroundColor Cyan
    Write-Host "           GERENCIADOR & INSTALADOR DEPLOY DOCKER PHP ENTERPRISE          " -ForegroundColor Yellow
    Write-Host "   Traefik v2.11 + ModSecurity WAF + Antivírus ClamAV + FrankenPHP Worker " -ForegroundColor Green
    Write-Host "==========================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Ensure-EnvFile {
    if (-not (Test-Path "$root\.env")) {
        Write-Host "-> Arquivo .env não encontrado. Criando a partir de .env.example..." -ForegroundColor Yellow
        if (Test-Path "$root\.env.example") {
            Copy-Item "$root\.env.example" "$root\.env"
            Write-Host " [OK] Arquivo .env inicializado com sucesso." -ForegroundColor Green
        }
    }
}

function Update-ActiveVersionInDynamicYml($versionShort) {
    # versionShort ex: "php82", "php83", "php84", "php85", "php74"
    $dynamicFile = "$root\load-balance\dynamic.yml"
    if (Test-Path $dynamicFile) {
        $content = Get-Content $dynamicFile -Raw
        $targetUrl = "http://app_waf_$versionShort:8080"
        $newContent = [System.Text.RegularExpressions.Regex]::Replace(
            $content,
            '(service-cluster-lb:\s*\r?\n\s*loadBalancer:\s*\r?\n\s*servers:\s*\r?\n\s*-\s*url:\s*")([^"]+)(")',
            "`${1}$targetUrl`$3"
        )
        Set-Content -Path $dynamicFile -Value $newContent -Encoding UTF8
        Write-Host " [OK] Traefik configurado para apontar a porta 80/443 diretamente para $versionShort ($targetUrl)" -ForegroundColor Green
    }
}

function Update-EnvVar($key, $value) {
    $envFile = "$root\.env"
    if (Test-Path $envFile) {
        $lines = Get-Content $envFile
        $found = $false
        $newLines = @()
        foreach ($line in $lines) {
            if ($line -match "^$key=") {
                $newLines += "$key=$value"
                $found = $true
            } else {
                $newLines += $line
            }
        }
        if (-not $found) {
            $newLines += "$key=$value"
        }
        Set-Content -Path $envFile -Value $newLines -Encoding UTF8
    }
}

function Generate-SslCertificates {
    Write-Host "`n==> Gerando Certificados SSL Locais (pasta ./ssl/certs)..." -ForegroundColor Cyan
    if (-not (Test-Path "$root\ssl\certs")) {
        New-Item -ItemType Directory -Path "$root\ssl\certs" -Force | Out-Null
    }
    
    # Tenta usar mkcert se existir no host
    if (Get-Command mkcert -ErrorAction SilentlyContinue) {
        Write-Host " -> Utilizando ferramenta oficial 'mkcert' do sistema..." -ForegroundColor Gray
        mkcert -cert-file "$root\ssl\certs\local-cert.pem" -key-file "$root\ssl\certs\local-key.pem" localhost 127.0.0.1 ::1 docker.charlescorrea.com.br
    } else {
        Write-Host " -> mkcert não detectado no host. Gerando certificado RSA 2048-bit via container Docker isolado..." -ForegroundColor Gray
        docker run --rm -v "${root}/ssl/certs:/certs" alpine sh -c "apk add --no-cache openssl && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/local-key.pem -out /certs/local-cert.pem -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,DNS:docker.charlescorrea.com.br,IP:127.0.0.1'"
    }

    # Assegura a permissão do acme.json
    if (-not (Test-Path "$root\ssl\letsencrypt")) {
        New-Item -ItemType Directory -Path "$root\ssl\letsencrypt" -Force | Out-Null
    }
    docker run --rm -v "${root}/ssl/letsencrypt:/letsencrypt" alpine sh -c "touch /letsencrypt/acme.json && chmod 600 /letsencrypt/acme.json"

    Write-Host " [OK] Certificados gerados com sucesso em ./ssl/certs/ (local-cert.pem e local-key.pem)!" -ForegroundColor Green
    Write-Host " [OK] Arquivo ./ssl/letsencrypt/acme.json configurado com permissão 600 para Let's Encrypt." -ForegroundColor Green
}

function Ensure-DependencyInstalled($cmdName, $wingetId, $chocoId, $friendlyName) {
    if (-not (Get-Command $cmdName -ErrorAction SilentlyContinue)) {
        Write-Host " [!] $friendlyName não detectado no sistema." -ForegroundColor Yellow
        Write-Host " -> Tentando instalar $friendlyName automaticamente via gerenciador de pacotes..." -ForegroundColor Cyan
        
        $installed = $false
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "    -> Executando: winget install --id $wingetId -e --accept-package-agreements --accept-source-agreements" -ForegroundColor Gray
            & winget install --id $wingetId -e --accept-package-agreements --accept-source-agreements --silent
            if ($LASTEXITCODE -eq 0) { $installed = $true }
        }
        
        if (-not $installed -and (Get-Command choco -ErrorAction SilentlyContinue)) {
            Write-Host "    -> Executando fallback: choco install $chocoId -y" -ForegroundColor Gray
            & choco install $chocoId -y
            if ($LASTEXITCODE -eq 0) { $installed = $true }
        }

        # Atualiza PATH da sessão atual
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        if (Get-Command $cmdName -ErrorAction SilentlyContinue) {
            Write-Host " [OK] $friendlyName instalado com sucesso!" -ForegroundColor Green
        } else {
            Write-Host " [AVISO] $friendlyName foi instalado ou necessita reinicialização do terminal/Windows." -ForegroundColor Yellow
        }
    } else {
        Write-Host " [OK] $friendlyName já está instalado." -ForegroundColor Green
    }
}

function Check-And-Install-Dependencies {
    Write-Host "-> Verificando dependências essenciais do ecossistema..." -ForegroundColor Gray
    
    # 1. Git
    Ensure-DependencyInstalled "git" "Git.Git" "git" "Git"
    
    # 2. mkcert (utilitário SSL local de alta confiança)
    Ensure-DependencyInstalled "mkcert" "FiloSottile.mkcert" "mkcert" "mkcert (Gerador SSL Confiável)"

    # 3. Docker e Docker Compose
    $hasDocker = (Get-Command docker -ErrorAction SilentlyContinue)
    $hasCompose = $false
    if ($hasDocker) {
        try {
            $null = docker compose version 2>$null
            if ($LASTEXITCODE -eq 0) { $hasCompose = $true }
        } catch { }
    }

    if (-not $hasDocker -or -not $hasCompose) {
        Write-Host " [!] Docker Desktop ou Docker Compose não detectado." -ForegroundColor Yellow
        Write-Host " -> Instalando Docker Desktop automaticamente..." -ForegroundColor Cyan
        
        $installedDocker = $false
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "    -> Executando: winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements" -ForegroundColor Gray
            & winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) { $installedDocker = $true }
        }
        
        if (-not $installedDocker -and (Get-Command choco -ErrorAction SilentlyContinue)) {
            Write-Host "    -> Executando: choco install docker-desktop -y" -ForegroundColor Gray
            & choco install docker-desktop -y
            if ($LASTEXITCODE -eq 0) { $installedDocker = $true }
        }

        if (-not $installedDocker) {
            Write-Host "    -> Baixando instalador oficial do Docker Desktop via PowerShell..." -ForegroundColor Gray
            $installerPath = "$env:TEMP\DockerDesktopInstaller.exe"
            Invoke-WebRequest -Uri "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -OutFile $installerPath
            Write-Host "    -> Iniciando instalador silencioso do Docker Desktop..." -ForegroundColor Gray
            Start-Process -FilePath $installerPath -ArgumentList "install --quiet --accept-license" -Wait
        }

        # Atualiza o PATH da sessão corrente
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        Write-Host " [AVISO] Docker Desktop instalado!" -ForegroundColor Green
        Write-Host " Se esta for a primeira instalação, pode ser necessário reiniciar o Windows ou iniciar o aplicativo 'Docker Desktop'." -ForegroundColor Yellow
    }

    # Validação final se o serviço Docker está ativo
    try {
        $null = docker info 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host " [OK] Docker Engine ativo e operacional." -ForegroundColor Green
        } else {
            Write-Host " [!] O Docker está instalado, mas o serviço Docker Desktop parece fechado." -ForegroundColor Yellow
            Write-Host " -> Tentando iniciar o Docker Desktop automaticamente..." -ForegroundColor Cyan
            $dockerApp = "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
            if (Test-Path $dockerApp) {
                Start-Process $dockerApp
                Write-Host " -> Aguardando 15 segundos para inicialização do daemon..." -ForegroundColor Gray
                Start-Sleep -Seconds 15
            }
        }
    } catch { }
}

function Run-RequirementsCheck {
    if (Test-Path "$root\_Install\check_requirements.ps1") {
        Write-Host "-> Validando requisitos de hardware e recursos do Docker..." -ForegroundColor Gray
        & "$root\_Install\check_requirements.ps1"
        if ($LASTEXITCODE -ne 0) {
            Write-Host " [AVISO] Requisitos mínimos não atingidos, mas você pode continuar se desejar." -ForegroundColor Yellow
        }
        Write-Host ""
    }
}

Show-Header
Ensure-EnvFile
Check-And-Install-Dependencies
Run-RequirementsCheck

Write-Host "Escolha como deseja rodar o cluster Docker PHP (Porta 80 e 443 ativas no Traefik):" -ForegroundColor White
Write-Host ""
Write-Host "  --- SUBIR UMA VERSÃO ESPECÍFICA (Acessível na Porta 80 e 443) ---" -ForegroundColor Yellow
Write-Host "  [1] Ativar PHP 7.4 (Apache mod_php + WAF + Traefik na porta 80/443)" -ForegroundColor White
Write-Host "  [2] Ativar PHP 8.2 (FrankenPHP Worker + WAF + Traefik na porta 80/443)" -ForegroundColor White
Write-Host "  [3] Ativar PHP 8.3 (FrankenPHP Worker + WAF + Traefik na porta 80/443)" -ForegroundColor White
Write-Host "  [4] Ativar PHP 8.4 (FrankenPHP Worker + WAF + Traefik na porta 80/443)" -ForegroundColor White
Write-Host "  [5] Ativar PHP 8.5 (FrankenPHP Worker + WAF + Traefik na porta 80/443)" -ForegroundColor White
Write-Host ""
Write-Host "  --- MODO CLUSTER COMPLETO & MONITORAMENTO ---" -ForegroundColor Yellow
Write-Host "  [6] Subir Cluster Completo (Traefik + Todos os PHPs em rotas /php74, /php82...)" -ForegroundColor Cyan
Write-Host "  [7] Subir Sentinela de Recursos & Antivírus (app_monitor + app_clamav)" -ForegroundColor Green
Write-Host "  [8] Disparar Varredura Manual Imediata do Antivírus ClamAV (/scandata)" -ForegroundColor Green
Write-Host "  [9] Gerar / Regenerar Certificados SSL (pasta ./certs e ./letsencrypt)" -ForegroundColor Cyan
Write-Host "  [10] Configurar opções no arquivo .env (Replicas, Domínio, Cache, Antivírus)" -ForegroundColor Yellow
Write-Host "  [11] Parar todos os containers do projeto" -ForegroundColor Magenta
Write-Host "  [0] Sair" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Digite a opção desejada [0-11]"

switch ($choice) {
    "1" {
        Write-Host "`n==> Configurando e ativando PHP 7.4 na Porta 80/443..." -ForegroundColor Cyan
        Update-ActiveVersionInDynamicYml "php74"
        Update-EnvVar "PHP_ACTIVE_VERSION" "7.4"
        Update-EnvVar "COMPOSE_PROJECT_NAME" "php74"
        docker compose -p php74 up -d --build app_traefik_loadbalance app_waf_php74 app_php74
        Write-Host "`n[SUCESSO] PHP 7.4 está ativo e respondendo na porta 80 e 443!" -ForegroundColor Green
        Write-Host " -> Gateway HTTP (Porta 80):  http://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Gateway HTTPS (Porta 443): https://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Dashboard Protegido:       https://localhost/load-balance/ (Login Basic Auth)" -ForegroundColor Gray
    }
    "2" {
        Write-Host "`n==> Configurando e ativando PHP 8.2 na Porta 80/443..." -ForegroundColor Cyan
        Update-ActiveVersionInDynamicYml "php82"
        Update-EnvVar "PHP_ACTIVE_VERSION" "8.2"
        Update-EnvVar "COMPOSE_PROJECT_NAME" "php82"
        docker compose -p php82 up -d --build app_traefik_loadbalance app_waf_php82 app_php82
        Write-Host "`n[SUCESSO] PHP 8.2 está ativo e respondendo na porta 80 e 443!" -ForegroundColor Green
        Write-Host " -> Gateway HTTP (Porta 80):  http://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Gateway HTTPS (Porta 443): https://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)" -ForegroundColor Gray
    }
    "3" {
        Write-Host "`n==> Configurando e ativando PHP 8.3 na Porta 80/443..." -ForegroundColor Cyan
        Update-ActiveVersionInDynamicYml "php83"
        Update-EnvVar "PHP_ACTIVE_VERSION" "8.3"
        Update-EnvVar "COMPOSE_PROJECT_NAME" "php83"
        docker compose -p php83 up -d --build app_traefik_loadbalance app_waf_php83 app_php83
        Write-Host "`n[SUCESSO] PHP 8.3 está ativo e respondendo na porta 80 e 443!" -ForegroundColor Green
        Write-Host " -> Gateway HTTP (Porta 80):  http://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Gateway HTTPS (Porta 443): https://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)" -ForegroundColor Gray
    }
    "4" {
        Write-Host "`n==> Configurando e ativando PHP 8.4 na Porta 80/443..." -ForegroundColor Cyan
        Update-ActiveVersionInDynamicYml "php84"
        Update-EnvVar "PHP_ACTIVE_VERSION" "8.4"
        Update-EnvVar "COMPOSE_PROJECT_NAME" "php84"
        docker compose -p php84 up -d --build app_traefik_loadbalance app_waf_php84 app_php84
        Write-Host "`n[SUCESSO] PHP 8.4 está ativo e respondendo na porta 80 e 443!" -ForegroundColor Green
        Write-Host " -> Gateway HTTP (Porta 80):  http://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Gateway HTTPS (Porta 443): https://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)" -ForegroundColor Gray
    }
    "5" {
        Write-Host "`n==> Configurando e ativando PHP 8.5 na Porta 80/443..." -ForegroundColor Cyan
        Update-ActiveVersionInDynamicYml "php85"
        Update-EnvVar "PHP_ACTIVE_VERSION" "8.5"
        Update-EnvVar "COMPOSE_PROJECT_NAME" "php85"
        docker compose -p php85 up -d --build app_traefik_loadbalance app_waf_php85 app_php85
        Write-Host "`n[SUCESSO] PHP 8.5 está ativo e respondendo na porta 80 e 443!" -ForegroundColor Green
        Write-Host " -> Gateway HTTP (Porta 80):  http://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Gateway HTTPS (Porta 443): https://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)" -ForegroundColor Gray
    }
    "6" {
        Write-Host "`n==> Construindo e subindo Cluster Completo com Traefik Load Balancer..." -ForegroundColor Cyan
        Update-EnvVar "COMPOSE_PROJECT_NAME" "php_cluster"
        docker compose -p php_cluster up -d --build
        Write-Host "`n[SUCESSO] Cluster Completo ativo e operacional!" -ForegroundColor Green
        Write-Host " -> Traefik HTTP (Porta 80):   http://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Traefik HTTPS (Porta 443): https://localhost/info.php" -ForegroundColor Yellow
        Write-Host " -> Traefik Dashboard:         https://localhost/load-balance/ (Login Basic Auth)" -ForegroundColor Gray
    }
    "7" {
        Write-Host "`n==> Construindo e subindo Sentinela de Recursos & Antivírus ClamAV..." -ForegroundColor Cyan
        docker compose up -d --build app_clamav app_monitor
        Write-Host "[OK] Sentinela (app_monitor) e Antivírus (app_clamav) iniciados com sucesso!" -ForegroundColor Green
    }
    "8" {
        Write-Host "`n==> Executando varredura imediata com o Antivírus ClamAV em /scandata..." -ForegroundColor Cyan
        docker compose exec app_monitor clamdscan --server=app_clamav --port=3310 --fdpass --infected --multiscan /scandata
    }
    "9" {
        Generate-SslCertificates
    }
    "10" {
        Write-Host "`n==> Configuração Interativa de Variáveis (.env):" -ForegroundColor Cyan
        $dom = Read-Host "Domínio da Aplicação (Enter para manter atual ou 'localhost')"
        if ($dom) { Update-EnvVar "DOMAIN" $dom }
        $email = Read-Host "E-mail para Let's Encrypt SSL (Enter para manter)"
        if ($email) { Update-EnvVar "LETSENCRYPT_EMAIL" $email }
        $cache = Read-Host "Habilitar Cache no Traefik? [s/n]"
        if ($cache -eq 's' -or $cache -eq 'S') { Update-EnvVar "ENABLE_CACHE" "true" }
        elseif ($cache -eq 'n' -or $cache -eq 'N') { Update-EnvVar "ENABLE_CACHE" "false" }
        Write-Host " [OK] Configurações atualizadas no arquivo .env!" -ForegroundColor Green
    }
    "11" {
        Write-Host "`n==> Parando todos os containers..." -ForegroundColor Magenta
        docker compose down
        Write-Host "[OK] Todos os containers foram finalizados com sucesso." -ForegroundColor Green
    }
    "0" {
        Write-Host "Saindo..." -ForegroundColor Gray
        exit 0
    }
    default {
        Write-Host "[ERRO] Opção inválida digitada: $choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Pressione qualquer tecla para finalizar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
