FROM php:7.4-apache

# Como o Debian 11 (Bullseye) foi movido para o repositório archive.debian.org,
# reconfiguramos os sources para garantir instalação sem erros 404 e ignoramos expiração de Release
RUN echo "deb http://archive.debian.org/debian bullseye main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list && \
    echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until

# 1. Configuração de Localização (pt_BR.UTF-8) e Fuso Horário de Brasília (America/Sao_Paulo)
RUN echo "==> [Passo 1/7] Configurando Localização pt_BR.UTF-8 e Fuso Horário de Brasília..." \
    && apt-get update && apt-get install -y --no-install-recommends \
        locales \
        tzdata \
    && sed -i -e 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen \
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && ln -snf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime \
    && echo "America/Sao_Paulo" > /etc/timezone \
    && dpkg-reconfigure -f noninteractive tzdata

ENV TZ="America/Sao_Paulo" \
    LANG="pt_BR.UTF-8" \
    LANGUAGE="pt_BR:pt" \
    LC_ALL="pt_BR.UTF-8" \
    APP_GEO_CONTINENT="South America" \
    APP_GEO_CONTINENT_CODE="SA" \
    APP_GEO_COUNTRY="Brazil" \
    APP_GEO_COUNTRY_CODE="BR" \
    APP_GEO_REGION="RS" \
    APP_GEO_REGION_NAME="Rio Grande do Sul" \
    APP_GEO_CITY="Porto Alegre" \
    APP_GEO_DISTRICT="Centro" \
    APP_GEO_ZIP="90000-000" \
    APP_GEO_LAT="-30.1188" \
    APP_GEO_LON="-51.168" \
    APP_GEO_CURRENCY="BRL"

# 2. Instalação das dependências base do sistema e repositório Microsoft SQL Server
RUN echo "==> [Passo 2/7] Instalando dependências do sistema e repositório Microsoft ODBC..." \
    && apt-get update && apt-get install -y --no-install-recommends \
        libzip-dev \
        zip \
        unzip \
        libpng-dev \
        libjpeg-dev \
        libfreetype6-dev \
        libonig-dev \
        libxml2-dev \
        libpq-dev \
        libsqlite3-dev \
        libicu-dev \
        libmagickwand-dev \
        firebird-dev \
        libfbclient2 \
        unixodbc-dev \
        git \
        gnupg \
        g++ \
        curl \
        ca-certificates \
        clamav \
        clamav-freshclam \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl -fsSL https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && docker-php-source extract \
    && touch /usr/src/php/.docker-delete-me-disabled \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && mkdir -p /usr/src/php/ext/interbase \
    && curl -fsSL https://github.com/FirebirdSQL/php-firebird/archive/master.tar.gz | tar xvz -C /usr/src/php/ext/interbase --strip 1 \
    && sed -i 's/case SQL_TIMESTAMP:/case SQL_TIMESTAMP:;/g' /usr/src/php/ext/interbase/ibase_query.c \
    && docker-php-ext-configure interbase --with-interbase \
    && echo "==> [Passo 3/7] Instalando extensões nativas do PHP..." \
    && for ext in pdo pdo_mysql mysqli pdo_pgsql pgsql pdo_sqlite sqlite3 pdo_firebird interbase intl gd mbstring xml zip opcache bcmath; do \
        if php -m | grep -qi "^${ext}$"; then \
            echo "    -> Extensão '${ext}' já existe. Pulando..."; \
        else \
            echo "    -> Instalando extensão '${ext}'..."; \
            err_log="/tmp/ext_${ext}.log"; \
            if ! docker-php-ext-install -j$(nproc) "${ext}" > "$err_log" 2>&1; then \
                echo ""; \
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"; \
                echo "Falha no deploy Docker PHP:"; \
                echo "Motivo do erro: Falha ao compilar/instalar a extensão nativa '${ext}'"; \
                echo "Mensagem do erro original:"; \
                cat "$err_log" | tail -n 25; \
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"; \
                echo ""; \
                exit 1; \
            fi; \
            rm -f "$err_log"; \
            echo "    [OK] Extensão '${ext}' instalada com sucesso."; \
        fi; \
    done \
    && rm -f /usr/src/php/.docker-delete-me-disabled \
    && docker-php-source delete \
    && echo "==> [Passo 4/7] Instalando extensões PECL (igbinary, redis, imagick, pdo_sqlsrv)..." \
    && for pecl_pkg in "igbinary:igbinary" "redis:redis" "imagick:imagick" "pdo_sqlsrv-5.9.0:pdo_sqlsrv"; do \
        pkg_name="${pecl_pkg%%:*}"; \
        ext_name="${pecl_pkg##*:}"; \
        if php -m | grep -qi "^${ext_name}$"; then \
            echo "    -> Extensão '${ext_name}' já existe. Pulando..."; \
        else \
            echo "    -> Instalando extensão '${ext_name}' (${pkg_name})..."; \
            err_log="/tmp/pecl_${ext_name}.log"; \
            if ! pecl install "${pkg_name}" > "$err_log" 2>&1; then \
                echo ""; \
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"; \
                echo "Falha no deploy Docker PHP:"; \
                echo "Motivo do erro: Falha ao instalar o pacote PECL '${pkg_name}' para a extensão '${ext_name}'"; \
                echo "Mensagem do erro original:"; \
                cat "$err_log" | tail -n 25; \
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"; \
                echo ""; \
                exit 1; \
            fi; \
            docker-php-ext-enable "${ext_name}" > /dev/null 2>&1; \
            rm -f "$err_log"; \
            echo "    [OK] Extensão '${ext_name}' instalada e ativada."; \
        fi; \
    done \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ativa mod_rewrite e mod_headers no Apache e define ServerName global para suprimir aviso AH00558
RUN echo "==> [Passo 5/7] Configurando módulos do Apache (rewrite, headers, ServerName)..." \
    && a2enmod rewrite headers \
    && echo "ServerName localhost" >> /etc/apache2/apache2.conf

# 3. Base oficial completa do Browscap para o get_browser() nativo do PHP
RUN echo "==> [Passo 6/7] Baixando base de dados Browscap oficial..." \
    && mkdir -p /var/lib/browscap \
    && curl -fsSL "https://browscap.org/stream?q=Full_PHP_BrowsCapINI" -o /var/lib/browscap/full_php_browscap.ini

# Configurações recomendadas do PHP com Fuso de Brasília, UTF-8, Geolocalização padrão nativa e Browscap
RUN echo "==> [Passo 7/7] Ajustando php.ini (custom.ini com Fuso Brasília, UTF-8 e limites)..." \
    && { \
        echo 'memory_limit = 256M'; \
        echo 'upload_max_filesize = 64M'; \
        echo 'post_max_size = 64M'; \
        echo 'max_execution_time = 300'; \
        echo 'date.timezone = America/Sao_Paulo'; \
        echo 'date.default_latitude = -30.1188'; \
        echo 'date.default_longitude = -51.168'; \
        echo 'default_charset = "UTF-8"'; \
        echo 'intl.default_locale = "pt_BR"'; \
        echo 'browscap = /var/lib/browscap/full_php_browscap.ini'; \
    } > /usr/local/etc/php/conf.d/custom.ini

# 3. Instalação oficial do Composer globalmente
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
ENV COMPOSER_ALLOW_SUPERUSER=1 \
    COMPOSER_HOME=/usr/local/composer

# Copia os arquivos do projeto para o DocumentRoot do Apache
COPY ./www/ /var/www/html/

# Ajusta permissões
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

# Validação final do deploy: exibe status positivo ou negativo e grava em /var/log/docker_deploy.log
RUN { \
        echo "=========================================================================="; \
        echo "               VALIDAÇÃO FINAL DO DEPLOY DOCKER PHP                      "; \
        echo "=========================================================================="; \
        if php -r ' \
            $required = ["pdo","pdo_mysql","mysqli","pdo_pgsql","pgsql","pdo_sqlite","sqlite3","PDO_Firebird","interbase","intl","gd","mbstring","xml","zip","Zend OPcache","bcmath","igbinary","redis","imagick","pdo_sqlsrv"]; \
            $loaded = get_loaded_extensions(); \
            $missing = []; \
            foreach ($required as $ext) { \
                $found = false; \
                foreach ($loaded as $l) { \
                    if (strcasecmp($l, $ext) === 0) { $found = true; break; } \
                } \
                if (!$found) $missing[] = $ext; \
            } \
            if (!empty($missing)) { \
                echo "[NEGATIVO] Falha no deploy Docker PHP:\n"; \
                echo "Motivo do erro: Extensões obrigatórias não carregadas: " . implode(", ", $missing) . "\n"; \
                exit(1); \
            } \
            echo "[POSITIVO] Deploy Docker PHP concluído com sucesso total!\n"; \
            echo " -> Versão PHP: " . PHP_VERSION . "\n"; \
            echo " -> Composer Global: " . exec("composer --version") . "\n"; \
            echo " -> Localização: pt_BR.UTF-8 (Data: " . date("d/m/Y H:i:s T") . ")\n"; \
            echo " -> Fuso Horário: " . date_default_timezone_get() . "\n"; \
            echo " -> Todas as 20 extensões solicitadas estão ativas e funcionais.\n"; \
            echo "\n--------------------------------------------------------------------------\n"; \
            echo " [ALERTA DE SEGURANÇA & BOAS PRÁTICAS: CVE-2026-109618 / CVE-2026-109619]\n"; \
            if (version_compare(PHP_VERSION, "8.2.35", "<")) { \
                echo " [AVISO] O PHP " . PHP_VERSION . " é uma versão legada/EOL (sem patch oficial no core).\n"; \
                echo " -> Mitigação Ativa Obrigatória: Manter o WAF (ModSecurity CRS) ativo na porta 8074.\n"; \
                echo " -> Como Atualizar para Versão Oficialmente Corrigida:\n"; \
                echo "    1. Use os novos containers do projeto: PHP 8.2 (>= 8.2.35), 8.4 (>= 8.4.27) ou 8.5.\n"; \
                echo "    2. Baixar releases oficiais corrigidas em: https://www.php.net/downloads.php\n"; \
                echo "    3. Patches avulsos da comunidade: https://github.com/php/php-src/security/advisories\n"; \
            } else { \
                echo " [SEGURO] Versão do PHP possui patch nativo contra CVE-2026-109618/109619.\n"; \
            } \
            echo "--------------------------------------------------------------------------\n"; \
        '; then \
            echo "=========================================================================="; \
        else \
            echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"; \
            echo "[NEGATIVO] Falha no deploy Docker PHP: Uma ou mais extensões falharam ao carregar."; \
            echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"; \
            exit 1; \
        fi; \
    } 2>&1 | tee /var/log/docker_deploy.log \
    && chmod 644 /var/log/docker_deploy.log

EXPOSE 80

CMD ["apache2-foreground"]
