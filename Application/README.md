# 🐘 Camada de Aplicação PHP & FrankenPHP Worker

Esta camada abriga o código-fonte da aplicação e os ambientes de execução PHP de alta performance.

---

## ⚡ FrankenPHP & Worker Mode

Diferente do ciclo tradicional do PHP-FPM (onde cada requisição inicializa o interpretador do zero), o FrankenPHP utiliza **Worker Mode** (`worker /var/www/html/frankenphp-worker.php 4`):
- O código da aplicação é inicializado na memória RAM na subida do container.
- Requisições subsequentes são atendidas diretamente pelo worker em milissegundos.
- Coleta periódica de lixo (`gc_collect_cycles()`) e limite de requisições (`MAX_REQUESTS=1000`) para prevenção de memory leaks.

---

## 🌐 Detecção Inteligente de Ambientes no Worker

No arquivo `frankenphp-worker.php`, cada requisição recebe a identificação automática de ambiente injetada globalmente:
- **Local (Desenvolvimento)**: `localhost`, `127.0.0.1`, `::1`, `*.localhost`, `*.local`.
- **Homologação (Staging)**: `homologacao.charlescorrea.com.br`, `staging.*`, `hml.*`.
- **Produção (Live)**: `charlescorrea.com.br`, `www.charlescorrea.com.br` ou IPs públicos.
*(Caso a variável `APP_ENV` esteja definida no `.env`, ela possui prioridade).*

---

## 🩺 Painel de Diagnóstico do Cluster (`info.php`)

Disponível em `http://localhost/info.php`:
- Exibe o status em tempo real de **todos os 8 serviços principais da infraestrutura** (WAF, ClamAV, Honeypots IA e Robots, Traefik, Sentinela, SSL/TLS).
- Auditoria de versões e mitigação de vulnerabilidades `CVE-2026-109618` e `CVE-2026-109619`.
- Inspeção de diretivas do `php.ini` e extensões compiladas.

