<#
.SYNOPSIS
    Verifica se o ambiente cumpre os requisitos mínimos de hardware e software para o Docker 8.5.
#>

$minHostRamGB = 12.0
$recHostRamGB = 16.0
$minDockerRamGB = 4.0
$recDockerRamGB = 6.0
$minFreeDiskGB = 15.0

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "   Verificando Requisitos de Sistema (Docker 8.5)      " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

$hasErrors = $false

# 1. Verifica se Docker está instalado e em execução
try {
    $dockerInfoRaw = docker info --format "{{.MemTotal}}|{{.NCPU}}" 2>$null
    if (-not $dockerInfoRaw) {
        Write-Host " [ERRO] O Docker não está em execução ou não foi encontrado no PATH!" -ForegroundColor Red
        Write-Host "        Inicie o Docker Desktop / daemon do Docker antes de prosseguir." -ForegroundColor Yellow
        exit 1
    }
    $parts = $dockerInfoRaw.Split('|')
    $dockerMemBytes = [double]$parts[0]
    $dockerCpus = [int]$parts[1]
    $dockerMemGB = [math]::Round($dockerMemBytes / 1GB, 1)
} catch {
    Write-Host " [ERRO] Falha ao consultar o Docker: $_" -ForegroundColor Red
    exit 1
}

# 2. Verifica RAM física do Host (Windows)
try {
    $hostMemBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    $hostMemGB = [math]::Round($hostMemBytes / 1GB, 1)
} catch {
    $hostMemGB = 0
}

# 3. Verifica Espaço em Disco Livre no Drive atual
try {
    $currentDriveLetter = (Get-Location).Drive.Name
    $freeDiskBytes = (Get-PSDrive $currentDriveLetter).Free
    $freeDiskGB = [math]::Round($freeDiskBytes / 1GB, 1)
} catch {
    $freeDiskGB = 0
}

# --- Exibição e Validações ---

# Host RAM
if ($hostMemGB -ge $minHostRamGB) {
    Write-Host " [OK] Memória RAM do Host: $hostMemGB GB (Mínimo: $minHostRamGB GB | Recomendado: $recHostRamGB GB)" -ForegroundColor Green
} elseif ($hostMemGB -gt 0) {
    Write-Host " [ERRO] Memória RAM do Host insuficiente: $hostMemGB GB detectados." -ForegroundColor Red
    Write-Host "        Requisito mínimo: $minHostRamGB GB. Com ClamAV, WAF, FrankenPHP e Cron, 8 GB causará travamentos por falta de memória." -ForegroundColor Red
    $hasErrors = $true
}

# Docker RAM
if ($dockerMemGB -ge $minDockerRamGB) {
    Write-Host " [OK] Memória alocada para o Docker: $dockerMemGB GB (Mínimo: $minDockerRamGB GB | Recomendado: $recDockerRamGB GB)" -ForegroundColor Green
} else {
    Write-Host " [ERRO] Memória alocada no Docker insuficiente: apenas $dockerMemGB GB." -ForegroundColor Red
    Write-Host "        O ClamAV sozinho consome até 2.5 GB ao carregar a base de assinaturas." -ForegroundColor Red
    Write-Host "        Aumente a memória do Docker Desktop / WSL2 (em .wslconfig ou Configurações do Docker) para no mínimo $minDockerRamGB GB." -ForegroundColor Yellow
    $hasErrors = $true
}

# CPUs
if ($dockerCpus -ge 2) {
    Write-Host " [OK] Núcleos de CPU disponíveis no Docker: $dockerCpus núcleos" -ForegroundColor Green
} else {
    Write-Host " [AVISO] Apenas $dockerCpus núcleo detectado. Recomendado: 2 ou mais núcleos." -ForegroundColor Yellow
}

# Espaço em Disco
if ($freeDiskGB -ge $minFreeDiskGB) {
    Write-Host " [OK] Espaço Livre em Disco ($currentDriveLetter`:): $freeDiskGB GB (Mínimo: $minFreeDiskGB GB)" -ForegroundColor Green
} else {
    Write-Host " [ERRO] Espaço em disco insuficiente no drive $currentDriveLetter`: ($freeDiskGB GB livres)." -ForegroundColor Red
    Write-Host "        É necessário pelo menos $minFreeDiskGB GB para imagens, volumes e banco de assinaturas do ClamAV." -ForegroundColor Red
    $hasErrors = $true
}

Write-Host "-------------------------------------------------------" -ForegroundColor Cyan

if ($hasErrors) {
    Write-Host " [BLOQUEADO] O sistema não atende aos requisitos mínimos obrigatórios." -ForegroundColor Red
    Write-Host "             Corrija os pontos indicados acima antes de iniciar a infraestrutura." -ForegroundColor Red
    exit 1
} else {
    Write-Host " [SUCESSO] Todos os requisitos de hardware e ambiente foram atendidos!" -ForegroundColor Green
    exit 0
}
