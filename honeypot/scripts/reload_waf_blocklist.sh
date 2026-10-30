#!/bin/sh
# Recarrega o Nginx do WAF para aplicar novos IPs da blocklist dos honeypots.
# Executado pelo app_cronjobs (task "honeypot-blocklist-reload").
if nginx -t >/dev/null 2>&1; then
    nginx -s reload
    echo "[honeypot] WAF recarregado com blocklist atualizada."
else
    echo "[honeypot] ERRO: nginx -t falhou, reload abortado." >&2
    nginx -t
    exit 1
fi

