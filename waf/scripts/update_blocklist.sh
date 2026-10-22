#!/bin/sh
# Script para baixar a lista de IPs tóxicos do StopForumSpam e blindar o Nginx

echo "Baixando lista de IPs maliciosos..."
TEMP_FILE="/tmp/stopforumspam.txt"

# Baixa a lista de IPs do StopForumSpam e formata para o padrão do "geo" do Nginx (IP 1;)
wget -qO- https://www.stopforumspam.com/downloads/toxic_ip_cidr.txt | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' > $TEMP_FILE

# Baixa a lista de IPs do myip.ms (Users Submitted) e adiciona ao arquivo
# echo "Baixando lista de IPs do myip.ms (Users Submitted)..."
# wget -qO- https://myip.ms/files/blacklist/htaccess/latest_blacklist_users_submitted.txt | awk '/^deny from /{print $3" 1;"}' >> $TEMP_FILE

# Baixa a lista de IPs do myip.ms (Latest Blacklist) e adiciona ao arquivo
# echo "Baixando lista de IPs do myip.ms (Latest Blacklist)..."
# wget -qO- https://myip.ms/files/blacklist/htaccess/latest_blacklist.txt | awk '/^deny from /{print $3" 1;"}' >> $TEMP_FILE

# Baixa a lista do Blocklist.de (todos os IPs maliciosos reportados)
# echo "Baixando lista do Blocklist.de..."
# wget -qO- https://lists.blocklist.de/lists/all.txt | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' >> $TEMP_FILE

# Spamhaus DROP e EDROP (Redes controladas por criminosos)
echo "Baixando Spamhaus DROP/EDROP..."
wget -qO- https://www.spamhaus.org/drop/drop.txt | grep -v "^;" | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' >> $TEMP_FILE
wget -qO- https://www.spamhaus.org/drop/edrop.txt | grep -v "^;" | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' >> $TEMP_FILE

# FireHOL Level 1 (Consolidação de dezenas de DNSBLs sem falsos positivos)
echo "Baixando FireHOL Level 1..."
wget -qO- https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset | grep -v "^#" | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' >> $TEMP_FILE

# Bitwire-IT IP Blocklist
# echo "Baixando Bitwire-IT Blocklists..."
# wget -qO- https://raw.githubusercontent.com/bitwire-it/ipblocklist/refs/heads/main/tables/inbound/networks.txt | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' >> $TEMP_FILE
# wget -qO- https://raw.githubusercontent.com/bitwire-it/ipblocklist/refs/heads/main/tables/inbound/single_ips.txt | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' >> $TEMP_FILE

# AbuseIPDB via API (Nível de confiança >= 75)
echo "Baixando lista do AbuseIPDB..."
curl -s -G https://api.abuseipdb.com/api/v2/blacklist \
    -d confidenceMinimum=75 \
    -d limit=10000 \
    -H "Key: 6c90caca4bcf177981786140260b7a5e516aeb96c320d7bac94d8d3d6c062c454d81a72d17535a6b" \
    -H "Accept: application/json" | jq -r '.data[].ipAddress' | awk '/^[0-9a-fA-F:\.]+/{print $1" 1;"}' >> $TEMP_FILE



# Se o arquivo não estiver vazio (download teve sucesso)
if [ -s "$TEMP_FILE" ]; then
    # Remove IPs duplicados
    sort -u $TEMP_FILE > /tmp/stopforumspam_unique.txt
    mv /tmp/stopforumspam_unique.txt /etc/nginx/stopforumspam.txt
    # Remove IPs locais e de loopback (BOGONs) para não quebrar healthchecks e rede do Docker
echo "Removendo IPs locais/bogon da lista..."
sed -i '/^127\./d' /etc/nginx/stopforumspam.txt
sed -i '/^10\./d' /etc/nginx/stopforumspam.txt
sed -i '/^172\.\(1[6-9]\|2[0-9]\|3[0-1]\)\./d' /etc/nginx/stopforumspam.txt
sed -i '/^192\.168\./d' /etc/nginx/stopforumspam.txt

echo "Lista atualizada com sucesso. Recarregando o WAF..."
    nginx -s reload || true
else
    echo "Falha ao baixar as listas."
fi
