@echo off
chcp 65001 >nul
title Instalador Docker PHP Enterprise Multi-Versao

echo ==========================================================================
echo        GERENCIADOR & INSTALADOR DEPLOY DOCKER PHP ENTERPRISE
echo ==========================================================================
echo.
echo -> Iniciando rotinas do instalador automatizado via PowerShell...

where pwsh >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
    goto end
)

where powershell >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
    goto end
) else (
    echo [ERRO] PowerShell nao foi encontrado. Execute o instalador no Windows 10/11.
    pause
)

:end

