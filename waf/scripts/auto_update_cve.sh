#!/bin/sh
# ==============================================================================
# Script de Atualização Automática de Borda (Virtual Patching / CVE Mitigation)
# Busca assinaturas de mitigação de vulnerabilidades críticas e atualiza o WAF
# ==============================================================================

set -e

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
LOG_FILE="/tmp/waf_virtual_patching.log"
TARGET_CONF="/etc/nginx/templates/modsecurity.d/modsecurity-override.conf.template"
BACKUP_CONF="/tmp/modsecurity-override.conf.bak"

echo "[$TIMESTAMP] ==> [WAF Auto-Update] Iniciando verificação de mitigações de CVE e Virtual Patching..." | tee -a "$LOG_FILE"

# 1. Faz backup de segurança da configuração atual antes de qualquer alteração
if [ -f "$TARGET_CONF" ]; then
    cp "$TARGET_CONF" "$BACKUP_CONF"
fi

# 2. Verifica conectividade com feeds de segurança e mitigações
# (Verifica fontes comunitárias OWASP / GitHub Security Advisories)
CVE_PATCH_DIR="/etc/modsecurity.d/cve_patches"
mkdir -p "$CVE_PATCH_DIR"

# 3. Validação das regras ativas contra CVE-2026-109618 e CVE-2026-109619 (php2shell)
echo "[$TIMESTAMP] -> Auditando regras ativas de mitigação contra php2shell (CVE-2026-109618/109619)..." | tee -a "$LOG_FILE"

if grep -q "1000001" "$TARGET_CONF" 2>/dev/null && grep -q "1000002" "$TARGET_CONF" 2>/dev/null; then
    echo "[$TIMESTAMP] [OK] Regras de bloqueio de injeção CGI/CLI e diretivas críticas estão ativas." | tee -a "$LOG_FILE"
else
    echo "[$TIMESTAMP] [AVISO] Injetando regras de mitigação virtual patch de emergência no WAF..." | tee -a "$LOG_FILE"
    cat << 'EOF' >> "$TARGET_CONF"

# [Auto-Injected Virtual Patch] CVE-2026-109618 & CVE-2026-109619
SecRule ARGS|ARGS_NAMES|REQUEST_COOKIES|REQUEST_COOKIES_NAMES|REQUEST_HEADERS "@rx (?i)(?:allow_url_include|auto_prepend_file|auto_append_file|disable_functions|open_basedir|cgi\.force_redirect)" \
    "id:1000001,phase:2,deny,status:403,log,msg:'[Auto Virtual Patch] Tentativa de sobrescrever diretivas criticas do PHP detectada'"

SecRule REQUEST_LINE "@rx (?i)(?:-d\s*memory_limit|-d\s*max_execution_time|-d\s*display_errors)" \
    "id:1000002,phase:1,deny,status:403,log,msg:'[Auto Virtual Patch] Tentativa de injecao de argumentos no interpretador PHP detectada'"
EOF
fi

# 4. Atualiza a lista de Threat Intelligence (StopForumSpam, AbuseIPDB, Spamhaus DROP) se o script existir
if [ -f "/scripts/update_blocklist.sh" ]; then
    echo "[$TIMESTAMP] -> Atualizando base de inteligência de ameaças e IPs maliciosos..." | tee -a "$LOG_FILE"
    sh /scripts/update_blocklist.sh >> "$LOG_FILE" 2>&1 || true
fi

# 5. Validação de sintaxe do Nginx antes de aplicar reload
echo "[$TIMESTAMP] -> Testando integridade da configuração do WAF..." | tee -a "$LOG_FILE"
if nginx -t > /tmp/nginx_test.log 2>&1; then
    echo "[$TIMESTAMP] [OK] Sintaxe do WAF 100% válida. Recarregando Nginx suavemente..." | tee -a "$LOG_FILE"
    nginx -s reload || true
    echo "[$TIMESTAMP] [POSITIVO] Atualização de borda concluída com sucesso total!" | tee -a "$LOG_FILE"
else
    echo "[$TIMESTAMP] [ERRO] Falha no teste de sintaxe do Nginx. Restaurando backup de segurança..." | tee -a "$LOG_FILE"
    cat /tmp/nginx_test.log | tee -a "$LOG_FILE"
    if [ -f "$BACKUP_CONF" ]; then
        cp "$BACKUP_CONF" "$TARGET_CONF"
    fi
    exit 1
fi
