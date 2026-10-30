# Honeypots

Duas armadilhas independentes, roteadas pelo Traefik **antes** do WAF/PHP. Todo IP capturado vai para uma blocklist compartilhada que os WAFs carregam (`geo $bad_ip`) → bloqueio 403 no site inteiro.

> Fuso horário: **America/Sao_Paulo** · idioma **pt-BR** em todos os containers e logs.

```
honeypot/
├── IA/                      # Agentes de IA autônomos (LLM pentest/crawlers)
│   ├── moqesh/              # fonte oficial clonado (gitignored) - juliourena/moqesh
│   ├── Dockerfile.moqesh    # build adaptado (fix LICENSE + TZ/pt-BR)
│   ├── bridge/              # webhook Moqesh -> blocklist dos WAFs
│   └── lures/               # iscas: robots.txt + links invisíveis (PHP)
├── Robots/                  # Scanners, brute-force, exploit kits
│   ├── robots_honeypot.py   # iscas WP/phpMyAdmin/xmlrpc + tarpit
│   └── php/HoneypotField.php# campo honeypot para formulários
├── blocklist/honeypot_blocklist.txt   # "IP 1;" (geo do Nginx)
└── scripts/reload_waf_blocklist.sh    # reload do WAF (cron de 1h)
```

## Fluxo

| Honeypot | Rotas (Traefik, prioridade 500) | Bloqueio |
|---|---|---|
| **IA** (`app_honeypot_ia`) | `/.env` `/.git` `/.aws` `/internal` `/backup` `/staging` `/api-internal` | Moqesh pontua o comportamento; score ≥ `MOQESH_AUTO_BLOCK_SCORE` ou reuso de honeytoken → webhook → `app_honeypot_ia_bridge` → blocklist |
| **Robots** (`app_honeypot_robots`) | `/wp-login.php` `/wp-admin` `/xmlrpc.php` `/phpmyadmin` `/pma` `/adminer` `/vendor/phpunit` `/cgi-bin` shells `.php` `/robots-trap` … | `ROBOTS_BLOCK_THRESHOLD` acessos → blocklist. Tarpit prende o bot até 60s |

A blocklist é aplicada pela tarefa `honeypot-blocklist-reload` (Cronjobs, a cada 1h). Para aplicar na hora:

```bash
docker exec app_waf_php83 sh /scripts/reload_waf_blocklist.sh
```

## Primeira instalação

```bash
git clone --depth 1 https://github.com/juliourena/moqesh.git honeypot/IA/moqesh
docker compose up -d --build app_honeypot_ia app_honeypot_ia_bridge app_honeypot_robots
```

Variáveis no `.env`: `MOQESH_WEBHOOK_SECRET`, `MOQESH_ADMIN_PASSWORD`, `MOQESH_AUTO_BLOCK_SCORE`, `ROBOTS_BLOCK_THRESHOLD`, `HONEYPOT_WHITELIST`.

No Linux, permita escrita na blocklist pelos containers (uid 10001):
`chown -R 10001 honeypot/blocklist logs/docker/honeypot`

## Iscas na aplicação

1. Mescle `IA/lures/robots.txt` no `Application/robots.txt`.
2. Inclua `IA/lures/honeypot-lures.php` no rodapé do layout (links invisíveis).
3. Formulários: use `Robots/php/HoneypotField.php`.

## Dashboard do Moqesh

`https://honeypot.localhost` (basic auth do load balancer + login do Moqesh).

## Logs

- `logs/docker/honeypot/robots.log` e `ia-bridge.log` — eventos JSON (data/hora de Brasília)
- `logs/docker/<container>.log` — stdout/stderr de todos os containers (`app_log_collector`)

## Desbloquear um IP

Remova a linha do IP em `blocklist/honeypot_blocklist.txt` e rode o reload do WAF.

> ⚠️ `HONEYPOT_WHITELIST` deve conter seus IPs administrativos. Moqesh é **AGPL-3.0**: modificar o fonte e expor em rede exige publicar o código.

