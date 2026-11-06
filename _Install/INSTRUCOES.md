# Guia de instalação e manutenção operacional

Este diretório contém os scripts utilitários `manager.bat` e `manager.sh` para facilitar o gerenciamento do cluster Docker sem a necessidade de digitar comandos extensos no terminal.

## Repositórios e documentação oficial

* [Documentação oficial do Docker](https://docs.docker.com/)
* [Documentação do Docker Compose](https://docs.docker.com/compose/)
* [Repositório oficial do mkcert](https://github.com/FiloSottile/mkcert)
* [Documentação oficial do Traefik v2](https://doc.traefik.io/traefik/v2.11/)
* [Documentação ACME Let's Encrypt](https://letsencrypt.org/docs/)

## Pré-requisitos do ambiente

* **Docker**: Docker Desktop (Windows/macOS) ou Docker Engine nativo (Linux).
* **Docker Compose**: Integrado nas versões modernas do Docker (`docker compose`).
* **mkcert**: Opcional, para geração de autoridade certificadora local confiável.

## Arquitetura de certificados SSL

### Desenvolvimento local (`localhost`)
O Let's Encrypt não valida domínios locais nem endereços sem apontamento DNS público. Para navegar em `https://localhost` sem telas de alerta de autoridade inválida, o Traefik consome os certificados emitidos pelo `mkcert` mapeados no diretório `./ssl/certs`.

### Produção (`dominio.com.br`)
No ambiente de produção, utiliza-se o arquivo complementar `docker-compose.prod.yml`. Ele habilita o resolver ACME via desafio TLS-ALPN ou HTTP-01 direto no Traefik, gerando e renovando os certificados emitidos pelo Let's Encrypt. O domínio definido na variável `DOMAIN` do `.env` precisa estar com registro DNS tipo A apontando para o IP público do servidor antes de subir a pilha.

## Execução dos scripts gerenciadores

* **Windows**: Execute `manager.bat` (duplo clique ou via prompt de comando).
* **Linux / macOS**: Execute `./_Install/manager.sh` (conceda permissão prévia com `chmod +x manager.sh`).

Ambos os scripts aceitam modo interativo por menu numérico ou passagem direta de parâmetro (exemplo: `manager.bat start`).

## Ações disponíveis no gerenciador

### Operação do cluster
* `start` (Opção 1): Sobe a pilha padrão com certificados locais (`docker compose up -d`).
* `start-prod` (Opção 2): Sobe a pilha unindo `docker-compose.yml` e `docker-compose.prod.yml` com Let's Encrypt ativado.
* `stop` (Opção 3): Encerra os contêineres e desconecta as redes (`docker compose down`).
* `restart` (Opção 4): Executa a parada e reinicialização completa dos serviços.
* `build` (Opção 5): Reconstrói as imagens dos contêineres a partir dos Dockerfiles locais.
* `logs` (Opção 6): Acompanha a saída de logs unificada de todos os serviços (`docker compose logs -f`).
* `shell` (Opção 7): Abre um terminal interativo dentro do contêiner PHP da aplicação.

### Dependências e ativos frontend
* `install-deps` (Opção 8): Executa `composer install` e `npm install` dentro do contêiner.
* `update-deps` (Opção 9): Executa `composer update` e `npm update`.
* `npm-dev` (Opção 10): Inicia o servidor de desenvolvimento do Vite em modo observador.
* `npm-build` (Opção 11): Compila os ativos do frontend para o diretório de distribuição.
* `update-docker` (Opção 12): Reconstrói os contêineres sem reaproveitar cache de camadas (`--no-cache`).
* `dump-autoload` (Opção 13): Atualiza o mapa de classes do Composer (`composer dump-autoload`).
* `clear-all-caches` (Opção 14): Limpa caches do Composer, NPM, Vite e camadas residuais de build.

### WAF ModSecurity e Nginx
* `waf-logs` (Opção 15): Acompanha os logs em tempo real das instâncias de WAF.
* `waf-shell` (Opção 16): Abre um terminal interativo no contêiner do WAF selecionado.
* `waf-test` (Opção 17): Valida a sintaxe dos arquivos de configuração Nginx (`nginx -t`).
* `waf-reload` (Opção 18): Recarrega as configurações e regras CRS sem encerrar conexões ativas (`nginx -s reload`).

### FrankenPHP, JIT e depuração
* `app-restart` (Opção 19): Reinicia apenas o contêiner PHP da aplicação.
* `frankenphp-reload` (Opção 20): Aplica recarga suave no servidor Caddy/FrankenPHP.
* `jit-enable` (Opção 21): Desativa extensões de depuração para liberar a compilação nativa JIT.
* `jit-disable` (Opção 22): Reativa extensões como Xdebug e profilers para depuração.
* `jit-status` (Opção 23): Consulta as métricas ativas de compilação da CPU e uso de buffer JIT.

### Segurança, certificados e antivírus
* `ssl-generate` (Opção 24): Gera novos pares de certificados locais com `mkcert` para `localhost` e `127.0.0.1`.
* `clamav-scan` (Opção 25): Dispara uma varredura manual de vírus no diretório `/scandata`.
* `clamav-logs` (Opção 26): Exibe o log de atualização de assinaturas e eventos do ClamAV.

### Gestão e limpeza de logs
* `logs-list` (Opção 27): Lista os arquivos de log gravados no diretório `./logs/`.
* `logs-tail` (Opção 28): Inspeciona o tamanho e as últimas linhas gravadas nos logs.
* `logs-clear` (Opção 29): Zera os arquivos de log mantendo a estrutura de diretórios intacta.

### Diagnóstico do Windows (WSL)
* `wsl-list` (Opção 30): Lista o estado e as versões das distribuições instaladas no WSL.
* `wsl-shutdown` (Opção 31): Encerra o subsistema WSL2 para liberação de memória RAM e resolução de bloqueios de socket do Docker Desktop.

## Política de retenção de registros

Os arquivos gerados no diretório `./logs/` passam por expurgo diário executado pelo serviço Sentinela. O parâmetro `LOG_RETENTION_DAYS=60` no `.env` define a idade máxima de retenção antes da remoção definitiva dos arquivos antigos.
