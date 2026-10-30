# 🐘 Imagens e Builds das Versões do PHP & Log Collector

Este diretório contém os `Dockerfiles` e contextos de build das diferentes versões suportadas pelo cluster, além do coletor centralizado de logs dos contêineres.

---

## 📁 Estrutura de Arquivos

```text
docker/
├── log-collector/        # Serviço em Python/Docker API para persistência contínua de stdout/stderr
│   ├── Dockerfile
│   └── collector.py
├── php7.4/               # Imagem PHP 7.4 (Apache mod_php legado para compatibilidade)
│   └── Dockerfile
├── php8.2/               # Imagem PHP 8.2 (FrankenPHP Worker Mode + Caddy)
│   └── Dockerfile
├── php8.3/               # Imagem PHP 8.3 (FrankenPHP Worker Mode + Caddy)
│   └── Dockerfile
├── php8.4/               # Imagem PHP 8.4 (FrankenPHP Worker Mode + Caddy)
│   └── Dockerfile
└── php8.5/               # Imagem PHP 8.5 (FrankenPHP Worker Mode + Caddy - bleeding edge)
    └── Dockerfile
```

---

## ⚡ Detalhes das Imagens

1. **FrankenPHP Worker Mode (PHP 8.2 a 8.5)**:
   - Mantém a aplicação persistida em memória RAM, eliminando o overhead de boot tradicional do PHP-FPM a cada requisição.
   - Suporte nativo a extensões modernas (OPcache, JIT, Redis, PDO, GD, etc.).
   - Execução sob usuário restrito não-root e flag `security_opt: [no-new-privileges:true]`.

2. **Log Collector (`app_log_collector`)**:
   - Escuta em streaming contínuo a API do Docker Socket (`docker logs -f`).
   - Grava os outputs individuais em `logs/docker/<container_name>.log` com carimbo de data/hora no fuso de Brasília.

