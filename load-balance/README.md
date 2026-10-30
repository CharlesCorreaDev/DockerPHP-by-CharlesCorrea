# ⚖️ Camada de Borda & Load Balancer (Traefik v2.11)

Esta camada é o **ponto único de entrada (Edge Gateway)** do cluster nas portas `80` (HTTP) e `443` (HTTPS), atuando como proxy reverso, terminador TLS e roteador prioritário antes que qualquer tráfego chegue ao WAF, PHP ou Honeypots.

---

## 🏗️ Como Funciona a Borda

1. **Terminação TLS Nativa**:
   - Carrega certificados locais (`mkcert` em `ssl/certs/`) ou certificados automáticos de produção via **Let's Encrypt ACME** (`ssl/letsencrypt/acme.json`).
2. **Priorização Inteligente de Rotas (`dynamic.yml`)**:
   - `priority: 9000` -> **Honeypots**: Intercepta rotas de agentes de IA (`/.env`, `/.git`, `/internal`) e scanners (`/wp-login.php`, `/phpmyadmin`) antes que toquem no WAF ou PHP.
   - `priority: 2000` -> **Healthchecks**: `/healthz` e `/ping` respondem instantaneamente `200 OK` na borda sem onerar os backends.
   - `priority: 1000` -> **Dashboard Traefik**: Interface `/load-balance/` e `/api` protegida com HTTP Basic Auth.
   - `priority: 100` -> **Tráfego de Aplicação**: Roteia o tráfego legítimo para o cluster WAF Nginx (`http://app_waf_php83:8080`).

---

## 🔌 Plugins Oficiais Integrados (`traefik.yml`)

- **`traefik-real-ip`**: Restaura e valida o IP real do cliente atrás de proxies reversos e CDN Cloudflare.
- **`bad-bot-blocker`**: Bloqueia na borda scanners e ferramentas conhecidas de intrusão (`sqlmap`, `nikto`, etc.).
- **`torblock`**: Bloqueio em tempo real de nós de saída da rede Tor.
- **`validate-headers`**: Exige cabeçalhos essenciais como `User-Agent` válido.
- **`corspreflight`**: Resposta `204 No Content` automática na borda para preflights `OPTIONS`.
- **`mw-security-headers`**: Camuflagem de resposta simulando `Server: Microsoft-IIS/10.0` e `X-Powered-By: ASP.NET`.

---

## 📁 Estrutura de Arquivos

```text
load-balance/
├── traefik.yml      # Configuração estática (entrypoints 80/443, plugins e logs)
├── dynamic.yml      # Configuração dinâmica (routers, middlewares, prioridades e services)
└── cache/           # Armazenamento de cache temporário da borda
```

