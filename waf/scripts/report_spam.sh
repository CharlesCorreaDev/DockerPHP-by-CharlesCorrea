#!/bin/sh
# Script para ler os logs do Nginx e reportar os vagabundos para o StopForumSpam
# Criado para rodar no container do WAF (Alpine) ou no servidor Host

API_KEY="c6ygtk3jrf0zdw"
if [ -f "/var/log/waf/access.log" ]; then
    LOG_FILE="/var/log/waf/access.log"
else
    LOG_FILE="/var/log/nginx/access.log"
fi
CACHE_FILE="/tmp/reported_ips.txt"

# Cria o arquivo de cache se não existir
touch $CACHE_FILE

# Pega todos os IPs que tomaram o código 444 (Nossos bloqueios de Honeypot e Bot)
# e filtra para que sejam únicos.
BAD_IPS=$(awk '$9 == 444 {print $1}' $LOG_FILE | sort | uniq)

for IP in $BAD_IPS; do
    # Verifica se já reportamos esse IP recentemente
    if grep -q "$IP" "$CACHE_FILE"; then
        continue
    fi

    echo "Reportando IP suspeito: $IP"

    # Faz o POST para a API do StopForumSpam
    RESPONSE=$(curl -s -X POST "https://www.stopforumspam.com/add" \
        -d "username=hacker_bot" \
        -d "ip_addr=$IP" \
        -d "api_key=$API_KEY" \
        -d "evidence=Detectado+pelo+Honeypot+Nginx+(Erro+444)")

    # Se a resposta contiver success, anota no cache para não reportar duas vezes
    if echo "$RESPONSE" | grep -q "success"; then
        echo "IP $IP reportado com sucesso!"
        echo "$IP" >> "$CACHE_FILE"
    else
        echo "Falha ao reportar o IP $IP: $RESPONSE"
    fi
done

echo "Processamento concluído."
