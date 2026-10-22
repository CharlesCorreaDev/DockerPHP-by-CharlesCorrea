#!/usr/bin/env bash
# ==============================================================================
# Instalador & Gerenciador Interativo do Cluster Docker PHP (Linux & macOS)
# Suporta: Ativação de versão única na porta 80 e 443 (7.4, 8.2, 8.3, 8.4, 8.5),
# Cluster Completo, Geração e Renovação SSL, e gerenciamento de variáveis .env.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Cores do terminal
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
MAGENTA='\033[0;35m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

show_header() {
    clear
    echo -e "${CYAN}==========================================================================${NC}"
    echo -e "${YELLOW}           GERENCIADOR & INSTALADOR DEPLOY DOCKER PHP ENTERPRISE          ${NC}"
    echo -e "${GREEN}   Traefik v2.11 + ModSecurity WAF + Antivírus ClamAV + FrankenPHP Worker ${NC}"
    echo -e "${CYAN}==========================================================================${NC}"
    echo ""
}

ensure_env_file() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}-> Arquivo .env não encontrado. Copiando de .env.example...${NC}"
        if [ -f .env.example ]; then
            cp .env.example .env
            echo -e "${GREEN}[OK] Arquivo .env inicializado com sucesso.${NC}"
        fi
    fi
}

update_active_version_in_dynamic_yml() {
    local version_short="$1" # Ex: php82, php83, php84, php85, php74
    local dynamic_file="load-balance/dynamic.yml"
    if [ -f "$dynamic_file" ]; then
        local target_url="http://app_waf_${version_short}:8080"
        sed -i.bak -E "s|(url:[[:space:]]*\"http://app_waf_)[^\"]+(\")|\1${version_short}:8080\2|g" "$dynamic_file"
        rm -f "${dynamic_file}.bak"
        echo -e "${GREEN}[OK] Traefik dinâmico configurado para apontar porta 80/443 para ${version_short} (${target_url})${NC}"
    fi
}

update_env_var() {
    local key="$1"
    local value="$2"
    if [ -f .env ]; then
        if grep -q "^${key}=" .env; then
            sed -i.bak -E "s|^${key}=.*|${key}=${value}|g" .env
            rm -f .env.bak
        else
            echo "${key}=${value}" >> .env
        fi
    fi
}

generate_ssl_certificates() {
    echo -e "\n${CYAN}==> Gerando Certificados SSL Locais (pasta ./certs e ./letsencrypt)...${NC}"
    mkdir -p ssl/certs ssl/letsencrypt
    if command -v mkcert &> /dev/null; then
        echo -e "${GRAY} -> Utilizando ferramenta mkcert do host...${NC}"
        mkcert -cert-file ssl/certs/local-cert.pem -key-file ssl/certs/local-key.pem localhost 127.0.0.1 ::1 docker.charlescorrea.com.br
    else
        echo -e "${GRAY} -> Gerando par de chaves RSA 2048-bit via container Docker isolado...${NC}"
        docker run --rm -v "${PWD}/certs:/certs" alpine sh -c "apk add --no-cache openssl >/dev/null && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /ssl/certs/local-key.pem -out /ssl/certs/local-cert.pem -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,DNS:docker.charlescorrea.com.br,IP:127.0.0.1'"
    fi

    docker run --rm -v "${PWD}/letsencrypt:/letsencrypt" alpine sh -c "touch /ssl/letsencrypt/acme.json && chmod 600 /ssl/letsencrypt/acme.json"
    echo -e "${GREEN}[OK] Certificados gerados com sucesso!${NC}"
}

check_and_install_dependencies() {
    echo -e "${GRAY}-> Verificando dependências de sistema (Docker, Git, mkcert)...${NC}"
    
    local os_type="$(uname -s)"

    # 1. Verifica Git
    if ! command -v git &> /dev/null; then
        echo -e "${YELLOW}[!] Git não encontrado. Instalando automaticamente...${NC}"
        if [ "$os_type" = "Linux" ]; then
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y git curl
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y git curl
            elif command -v pacman &> /dev/null; then
                sudo pacman -Sy --noconfirm git curl
            fi
        elif [ "$os_type" = "Darwin" ]; then
            if command -v brew &> /dev/null; then
                brew install git curl
            fi
        fi
    fi

    # 2. Verifica Docker e Docker Compose
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        echo -e "${YELLOW}[!] Docker ou Docker Compose não detectado.${NC}"
        echo -e "${CYAN}-> Iniciando instalação automatizada do Docker...${NC}"

        if [ "$os_type" = "Linux" ]; then
            echo -e "${GRAY} -> Baixando e executando script oficial de instalação (get.docker.com)...${NC}"
            curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
            sudo sh /tmp/get-docker.sh
            rm -f /tmp/get-docker.sh

            echo -e "${GRAY} -> Adicionando usuário atual ($USER) ao grupo docker...${NC}"
            sudo usermod -aG docker "$USER" 2>/dev/null || true

            echo -e "${GRAY} -> Habilitando e iniciando serviço do Docker...${NC}"
            sudo systemctl enable docker 2>/dev/null || true
            sudo systemctl start docker 2>/dev/null || true
        elif [ "$os_type" = "Darwin" ]; then
            if command -v brew &> /dev/null; then
                echo -e "${GRAY} -> Instalando Docker Desktop via Homebrew Cask...${NC}"
                brew install --cask docker
                open /Applications/Docker.app || true
            else
                echo -e "${RED}[ERRO] No macOS, instale o Homebrew ou baixe o Docker Desktop diretamente.${NC}"
            fi
        fi
    fi

    # 3. Validação do Daemon Docker
    if ! docker info &> /dev/null; then
        echo -e "${YELLOW}[!] O serviço do Docker não está respondendo. Tentando iniciar...${NC}"
        if [ "$os_type" = "Linux" ]; then
            sudo systemctl start docker 2>/dev/null || true
        elif [ "$os_type" = "Darwin" ]; then
            open /Applications/Docker.app 2>/dev/null || true
            sleep 10
        fi
    fi

    if docker compose version &> /dev/null; then
        echo -e "${GREEN}[OK] Docker e Docker Compose operacionais.${NC}\n"
    else
        echo -e "${RED}[AVISO] Docker instalado, mas pode ser necessário reiniciar a sessão para permissões de grupo.${NC}\n"
    fi
}

run_requirements_check() {
    if [ -f "_Install/check_requirements.sh" ]; then
        echo -e "${GRAY}-> Validando requisitos de hardware e recursos do Docker...${NC}"
        bash "_Install/check_requirements.sh" || echo -e "${YELLOW}[AVISO] Requisitos mínimos de memória/disco podem ser insuficientes para ClamAV.${NC}"
        echo ""
    fi
}

show_header
ensure_env_file
check_and_install_dependencies
run_requirements_check

echo -e "Escolha como deseja rodar o cluster Docker PHP (Porta 80 e 443 ativas no Traefik):"
echo ""
echo -e "  ${YELLOW}--- SUBIR UMA VERSÃO ESPECÍFICA (Acessível na Porta 80 e 443) ---${NC}"
echo -e "  ${CYAN}[1]${NC} Ativar PHP 7.4 (Apache mod_php + WAF + Traefik na porta 80/443)"
echo -e "  ${CYAN}[2]${NC} Ativar PHP 8.2 (FrankenPHP Worker + WAF + Traefik na porta 80/443)"
echo -e "  ${CYAN}[3]${NC} Ativar PHP 8.3 (FrankenPHP Worker + WAF + Traefik na porta 80/443)"
echo -e "  ${CYAN}[4]${NC} Ativar PHP 8.4 (FrankenPHP Worker + WAF + Traefik na porta 80/443)"
echo -e "  ${CYAN}[5]${NC} Ativar PHP 8.5 (FrankenPHP Worker + WAF + Traefik na porta 80/443)"
echo ""
echo -e "  ${YELLOW}--- MODO CLUSTER COMPLETO & MONITORAMENTO ---${NC}"
echo -e "  ${GREEN}[6] Subir Cluster Completo (Traefik + Todos os PHPs em rotas /php74, /php82...)${NC}"
echo -e "  ${GREEN}[7] Subir Sentinela de Recursos & Antivírus (app_monitor + app_clamav)${NC}"
echo -e "  ${GREEN}[8] Disparar Varredura Manual Imediata do Antivírus ClamAV (/scandata)${NC}"
echo -e "  ${CYAN}[9] Gerar / Regenerar Certificados SSL (pasta ./certs e ./letsencrypt)${NC}"
echo -e "  ${YELLOW}[10] Configurar opções no arquivo .env (Replicas, Domínio, Cache, Antivírus)${NC}"
echo -e "  ${MAGENTA}[11] Parar todos os containers do projeto${NC}"
echo -e "  ${GRAY}[0] Sair${NC}"
echo ""

read -rp "Digite a opção desejada [0-11]: " choice

case "$choice" in
    1)
        echo -e "\n${CYAN}==> Configurando e ativando PHP 7.4 na Porta 80/443...${NC}"
        update_active_version_in_dynamic_yml "php74"
        update_env_var "PHP_ACTIVE_VERSION" "7.4"
        update_env_var "COMPOSE_PROJECT_NAME" "php74"
        docker compose -p php74 up -d --build app_traefik_loadbalance app_waf_php74 app_php74
        echo -e "\n${GREEN}[SUCESSO] PHP 7.4 ativo e respondendo na porta 80 e 443!${NC}"
        echo -e "${YELLOW} -> Gateway HTTP (Porta 80):  http://localhost/info.php${NC}"
        echo -e "${YELLOW} -> Gateway HTTPS (Porta 443): https://localhost/info.php${NC}"
        echo -e "${GRAY} -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)${NC}"
        ;;
    2)
        echo -e "\n${CYAN}==> Configurando e ativando PHP 8.2 na Porta 80/443...${NC}"
        update_active_version_in_dynamic_yml "php82"
        update_env_var "PHP_ACTIVE_VERSION" "8.2"
        update_env_var "COMPOSE_PROJECT_NAME" "php82"
        docker compose -p php82 up -d --build app_traefik_loadbalance app_waf_php82 app_php82
        echo -e "\n${GREEN}[SUCESSO] PHP 8.2 ativo e respondendo na porta 80 e 443!${NC}"
        echo -e "${YELLOW} -> Gateway HTTP (Porta 80):  http://localhost/info.php${NC}"
        echo -e "${YELLOW} -> Gateway HTTPS (Porta 443): https://localhost/info.php${NC}"
        echo -e "${GRAY} -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)${NC}"
        ;;
    3)
        echo -e "\n${CYAN}==> Configurando e ativando PHP 8.3 na Porta 80/443...${NC}"
        update_active_version_in_dynamic_yml "php83"
        update_env_var "PHP_ACTIVE_VERSION" "8.3"
        update_env_var "COMPOSE_PROJECT_NAME" "php83"
        docker compose -p php83 up -d --build app_traefik_loadbalance app_waf_php83 app_php83
        echo -e "\n${GREEN}[SUCESSO] PHP 8.3 ativo e respondendo na porta 80 e 443!${NC}"
        echo -e "${YELLOW} -> Gateway HTTP (Porta 80):  http://localhost/info.php${NC}"
        echo -e "${YELLOW} -> Gateway HTTPS (Porta 443): https://localhost/info.php${NC}"
        echo -e "${GRAY} -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)${NC}"
        ;;
    4)
        echo -e "\n${CYAN}==> Configurando e ativando PHP 8.4 na Porta 80/443...${NC}"
        update_active_version_in_dynamic_yml "php84"
        update_env_var "PHP_ACTIVE_VERSION" "8.4"
        update_env_var "COMPOSE_PROJECT_NAME" "php84"
        docker compose -p php84 up -d --build app_traefik_loadbalance app_waf_php84 app_php84
        echo -e "\n${GREEN}[SUCESSO] PHP 8.4 ativo e respondendo na porta 80 e 443!${NC}"
        echo -e "${YELLOW} -> Gateway HTTP (Porta 80):  http://localhost/info.php${NC}"
        echo -e "${YELLOW} -> Gateway HTTPS (Porta 443): https://localhost/info.php${NC}"
        echo -e "${GRAY} -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)${NC}"
        ;;
    5)
        echo -e "\n${CYAN}==> Configurando e ativando PHP 8.5 na Porta 80/443...${NC}"
        update_active_version_in_dynamic_yml "php85"
        update_env_var "PHP_ACTIVE_VERSION" "8.5"
        update_env_var "COMPOSE_PROJECT_NAME" "php85"
        docker compose -p php85 up -d --build app_traefik_loadbalance app_waf_php85 app_php85
        echo -e "\n${GREEN}[SUCESSO] PHP 8.5 ativo e respondendo na porta 80 e 443!${NC}"
        echo -e "${YELLOW} -> Gateway HTTP (Porta 80):  http://localhost/info.php${NC}"
        echo -e "${YELLOW} -> Gateway HTTPS (Porta 443): https://localhost/info.php${NC}"
        echo -e "${GRAY} -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)${NC}"
        ;;
    6)
        echo -e "\n${CYAN}==> Construindo e subindo Cluster Completo com Traefik Load Balancer...${NC}"
        update_env_var "COMPOSE_PROJECT_NAME" "php_cluster"
        docker compose -p php_cluster up -d --build
        echo -e "\n${GREEN}[SUCESSO] Cluster Completo ativo e operacional!${NC}"
        echo -e "${YELLOW} -> Traefik HTTP (Porta 80):   http://localhost/info.php${NC}"
        echo -e "${YELLOW} -> Traefik HTTPS (Porta 443): https://localhost/info.php${NC}"
        echo -e "${GRAY} -> Dashboard Traefik:         https://localhost/load-balance/ (Login Basic Auth)${NC}"
        ;;
    7)
        echo -e "\n${CYAN}==> Construindo e subindo Sentinela de Recursos & Antivírus ClamAV...${NC}"
        docker compose up -d --build app_clamav app_monitor
        echo -e "${GREEN}[OK] Sentinela (app_monitor) e Antivírus (app_clamav) iniciados com sucesso!${NC}"
        ;;
    8)
        echo -e "\n${CYAN}==> Executando varredura imediata com o Antivírus ClamAV em /scandata...${NC}"
        docker compose exec app_monitor clamdscan --server=app_clamav --port=3310 --fdpass --infected --multiscan /scandata
        ;;
    9)
        generate_ssl_certificates
        ;;
    10)
        echo -e "\n${CYAN}==> Configuração Interativa de Variáveis (.env):${NC}"
        read -rp "Domínio da Aplicação (Enter para manter atual ou 'localhost'): " dom
        [ -n "$dom" ] && update_env_var "DOMAIN" "$dom"
        read -rp "E-mail para Let's Encrypt SSL (Enter para manter): " email
        [ -n "$email" ] && update_env_var "LETSENCRYPT_EMAIL" "$email"
        read -rp "Habilitar Cache no Traefik? [s/n]: " cache
        if [ "$cache" = "s" ] || [ "$cache" = "S" ]; then
            update_env_var "ENABLE_CACHE" "true"
        elif [ "$cache" = "n" ] || [ "$cache" = "N" ]; then
            update_env_var "ENABLE_CACHE" "false"
        fi
        echo -e "${GREEN}[OK] Configurações atualizadas no arquivo .env!${NC}"
        ;;
    11)
        echo -e "\n${MAGENTA}==> Parando todos os containers do projeto...${NC}"
        docker compose down
        echo -e "${GREEN}[OK] Todos os containers foram finalizados com sucesso.${NC}"
        ;;
    0)
        echo -e "${GRAY}Saindo...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}[ERRO] Opção inválida digitada: $choice${NC}"
        exit 1
        ;;
esac
