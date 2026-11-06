# Docker PHP Enterprise - Multi-Versão (7.4, 8.2, 8.3, 8.4, 8.5)

Cluster Docker voltado a alta disponibilidade, observabilidade e segurança de borda. Suporta execução paralela de múltiplas versões do PHP, Load Balancer Traefik v2.11, WAF com OWASP ModSecurity CRS, armadilhas honeypot para agentes de IA e scanners, FrankenPHP em Worker Mode, antivírus ClamAV e agente Sentinela com telemetria e despacho de alertas em tempo real.

> Configuração regional: Fuso de Brasília (`America/Sao_Paulo`) e locale `pt-BR.UTF-8` em todos os contêineres e logs.

---

## Arquitetura e fluxo de tráfego

```mermaid
graph TD
    Client[Cliente / Agente IA / Scanner] -->|HTTP :80 / HTTPS :443| Traefik[Traefik v2.11 Load Balancer & Gateway]
    
    subgraph "Camada de Deception e Honeypots (honeypot/)"
        Traefik -->|Rotas de IA: /.env, /.git, /internal, /backup| HoneypotIA[Moqesh IA Honeypot :8080]
        HoneypotIA -->|Labirinto Token Exhaust / Drena Contexto| TrapIA[Labirinto Procedural]
        HoneypotIA -->|Webhook HMAC| Bridge[Honeypot Bridge :8090]
        
        Traefik -->|Rotas de Scanners: /wp-login.php, /phpmyadmin, shells| HoneypotRobots[Robots Honeypot :8081]
        HoneypotRobots -->|Detecção SQLi / RCE / Tarpit| AutoBlock[Bloqueio Automático]
        HoneypotRobots -->|Insistência >= 4 hits| TrollRedirect[Redirect Capitão Nascimento]
        
        Bridge -->|Injeta IP em geo $bad_ip| BlocklistShared[(honeypot_blocklist.txt)]
        HoneypotRobots -->|Injeta IP em geo $bad_ip| BlocklistShared
    end

    subgraph "Camada de Borda e WAF (waf/)"
        Traefik -->|Tráfego Legítimo| WAF[WAF OWASP ModSecurity CRS / Nginx]
        BlocklistShared -->|Reload Dinâmico| WAF
        WAF -->|Spoofing IIS 10.0 ASP.NET + Cloudflare| WAF
        WAF -->|Mitigação Virtual CVE-2026-109618 / 109619| WAF
    end
    
    subgraph "Camada de Aplicação (Application/ e docker/)"
        WAF -->|Proxy HTTP de Borda| PHPApp[PHP Engine Ativo]
        PHPApp -.->|Opção 1| PHP74[PHP 7.4 Apache mod_php]
        PHPApp -.->|Opção 2| PHP82[PHP 8.2 FrankenPHP Worker Mode]
        PHPApp -.->|Opção 3| PHP83[PHP 8.3 FrankenPHP Worker Mode]
        PHPApp -.->|Opção 4| PHP84[PHP 8.4 FrankenPHP Worker Mode]
        PHPApp -.->|Opção 5| PHP85[PHP 8.5 FrankenPHP Worker Mode]
    end

    subgraph "Camada de Automação e Coleta (Cronjobs/ e docker/log-collector/)"
        Cron[app_cronjobs Master-Cron] -->|Reload a cada 1h| WAF
        LogCollector[app_log_collector] -->|docker logs -f com timestamp BR| LogsDocker[logs/docker/*.log]
    end

    subgraph "Sentinela, Antivírus e Observabilidade (sentinela/ e antivirus/)"
        Monitor[Sentinela app_monitor] -->|Varredura Contínua /scandata| ClamAV[Antivírus ClamAV :3310]
        Monitor -->|Métricas > 70% CPU/RAM/Disco| Alerts[Canais de Alerta]
        Alerts --> Email[E-mail AWS SES / SMTP]
        Alerts --> Telegram[Telegram Bot API]
        Alerts --> SMS[SMS Legal Gateway]
    end
```

---

## Estrutura do projeto

```text
├── Application/              # Código da aplicação PHP (index.php e painel diagnóstico info.php)
├── honeypot/                 # Sistema de armadilhas e deception
│   ├── IA/                   # Honeypot contra agentes autônomos de IA e scanners LLM (Moqesh)
│   │   ├── moqesh/           # Repositório clonado e adaptado
│   │   ├── Dockerfile.moqesh # Build com tradução pt-BR e fuso de Brasília
│   │   ├── bridge/           # Webhook HMAC para sincronização com o WAF
│   │   └── lures/            # Iscas (robots.txt com Disallow e links ocultos em PHP)
│   ├── Robots/               # Honeypot para scanners e bots tradicionais
│   │   ├── robots_honeypot.py# Servidor de iscas com Tarpit, detecção de SQLi/RCE e redirect
│   │   └── php/              # Campos honeypot para formulários
│   ├── blocklist/            # Lista compartilhada lida pelo Nginx (geo $bad_ip)
│   └── scripts/              # Scripts de reload do WAF e validação DNSBL
├── Cronjobs/                 # Agendador de tarefas em segundo plano (Master-Cron)
├── docker/                   # Ambientes PHP (7.4 a 8.5) e coletor de logs
│   └── log-collector/        # Coleta de stdout/stderr dos contêineres em logs/docker
├── load-balance/             # Configurações do Traefik v2.11 (traefik.yml, dynamic.yml)
├── antivirus/                # Configurações do ClamAV e quarentena isolada
├── sentinela/                # Telemetria, integridade e radar CTIR Gov
├── waf/                      # Firewall WAF (OWASP ModSecurity CRS + Nginx)
├── logs/                     # Diretório centralizado de logs com retenção de 60 dias
│   └── docker/               # Arquivos individuais por serviço
└── ssl/                      # Certificados SSL/TLS (mkcert local e Let's Encrypt)
```

---

## Documentação por componente

Cada camada possui manual técnico dedicado com arquitetura, variáveis e comandos operacionais:

| Camada | Diretório | Finalidade e tecnologias | Manual |
| :--- | :---: | :--- | :---: |
| **Borda e Load Balancer** | [`load-balance/`](load-balance/) | Traefik v2.11, terminação TLS, regras anti-DoS e headers de segurança | [Ler Manual](load-balance/README.md) |
| **WAF e Firewall Web** | [`waf/`](waf/) | OWASP ModSecurity CRS, Nginx, camuflagem IIS/Cloudflare e mitigação | [Ler Manual](waf/README.md) |
| **Honeypots (IA e Bots)** | [`honeypot/`](honeypot/) | Moqesh (Token Exhaust para IA) e Honeypot de Scanners com Tarpit | [Ler Manual](honeypot/README.md) |
| **Aplicação e Worker** | [`Application/`](Application/) | FrankenPHP Worker Mode, roteamento dinâmico e diagnóstico `info.php` | [Ler Manual](Application/README.md) |
| **Automação e Cronjobs** | [`Cronjobs/`](Cronjobs/) | Orquestrador Master-Cron em Python executando no Docker Socket | [Ler Manual](Cronjobs/README.md) |
| **Sentinela Guardian** | [`sentinela/`](sentinela/) | Telemetria (> 70% CPU/RAM), radar CTIR Gov e alertas Telegram/Email/SMS | [Ler Manual](sentinela/README.md) |
| **Antivírus e Quarentena** | [`antivirus/`](antivirus/) | ClamAV Daemon (:3310), freshclam e quarentena isolada | [Ler Manual](antivirus/README.md) |
| **Certificados SSL/TLS** | [`ssl/`](ssl/) | Emissão local (mkcert/OpenSSL) e produção automática (Let's Encrypt) | [Ler Manual](ssl/README.md) |
| **Imagens Docker e PHP** | [`docker/`](docker/) | Contextos de build das versões do PHP (7.4 a 8.5) e coletor de logs | [Ler Manual](docker/README.md) |
| **Auditoria e Logs** | [`logs/`](logs/) | Centralização de logs, expurgo de 60 dias e persistência de alertas | [Ler Manual](logs/README.md) |
| **Instalação e Requisitos** | [`_Install/`](_Install/) | Checagem de hardware/Docker e scripts utilitários | [Ler Manual](_Install/INSTRUCOES.md) |

---

## Principais recursos de segurança

### 1. Honeypot para agentes de IA (Moqesh)
- Ativo sob rotas-isca: `/.env`, `/.git`, `/.aws`, `/internal`, `/backup`, `/staging`, `/api-internal`.
- Aplica técnica de **Token Exhaust**: gera respostas sintéticas procedurais para esgotar janelas de contexto e cotas de API do atacante.
- Avalia a pontuação comportamental da sessão. Se atingir o limite ou reutilizar credenciais isca, aciona o webhook HMAC na Honeypot Bridge e bloqueia o IP no cluster inteiro.
- Interface web com suporte a português brasileiro em `https://honeypot.localhost/`.

### 2. Honeypot para robôs e scanners
- Captura varreduras de ferramentas automatizadas (`sqlmap`, `nikto`, `masscan`, etc.).
- Rotas armadilha: `/wp-login.php`, `/wp-admin`, `/xmlrpc.php`, `/phpmyadmin`, `/pma`, `/adminer`, `/shell.php`, etc.
- Inspeciona payloads contra padrões de SQLi, injeção de comandos e leitura de arquivos do sistema.
- Responde com tarpit para reter a conexão do bot e gzip bomb.
- Se o atacante insistir em 4 ou mais requisições, recebe redirecionamento HTTP 302 para o vídeo do Capitão Nascimento.

### 3. Traefik v2.11 e blindagem de borda
- Terminação TLS nativa com HTTP/HTTPS nas portas 80 e 443.
- Roteamento prioritário (`priority: 9000`) para desviar ataques aos honeypots antes que alcancem o WAF ou o PHP.
- **Proteção contra DoS e estouro de payload**: middleware `mw-buffering` restringe requisições a 15 MB de corpo total e 2 MB em memória.
- **Cabeçalhos de proteção**:
  - HSTS de 1 ano com subdomínios e preload (`max-age=31536000; includeSubDomains; preload`).
  - Prevenção contra Clickjacking (`X-Frame-Options: SAMEORIGIN` e `frame-ancestors 'self'`).
  - Content Security Policy (CSP) controlando scripts, fontes e conexões.
  - Permissions-Policy bloqueando acesso a câmera, microfone, geolocalização e USB.
  - Isolamento Cross-Origin contra vazamentos laterais (`COOP: same-origin`, `CORP: same-origin`).
  - Camuflagem ativa simulando `Microsoft-IIS/10.0` e `ASP.NET`.

### 4. WAF OWASP ModSecurity CRS e Nginx
- Inspeção profunda de corpo e resposta contra ataques do OWASP Top 10.
- Bloqueio imediato de IPs listados em `geo $bad_ip` (alimentado pelos honeypots e listas de reputação).
- Mitigação virtual contra vulnerabilidades `CVE-2026-109618` e `CVE-2026-109619`.

### 5. Auditoria de serviços em tempo real (`info.php`)
Painel integrado em `http://localhost/info.php` que checa o status de operação dos 8 serviços da infraestrutura:
- WAF (ModSecurity CRS)
- Antivírus (ClamAV)
- Honeypot IA (Moqesh)
- Honeypot Robots e Scanners
- Honeypot Bridge (WAF Sync)
- Traefik Load Balancer
- Sentinela Guardian
- Camada Criptográfica SSL/TLS

### 6. Mitigação de vulnerabilidades do Kernel Linux
Os scripts de instalação e o `docker-compose.yml` contêm regras automáticas de contenção:
- **CVE-2026-74580 (Vghost)**: Descarregamento e bloqueio do módulo `vhost_net` e nós `/dev/vhost-*`.
- **CVE-2026-46300 (Fragnesia)**: Bloqueio dos módulos IPsec `esp4`/`esp6` e descarte irrestrito de capabilities de rede (`cap_drop: [ALL]`).
- **CVE-2026-31431 (Copy Fail)**: Bloqueio do módulo `algif_aead` e imposição de `no-new-privileges:true` em contêineres PHP e armadilhas.
- **CVE-2026-98432 (UAF no TCP/MPTCP)**: Desativação do Multipath TCP no host (`net.mptcp.enabled = 0`).
- **CVE-2026-53359 (Januscape)**: Isolamento de shadow MMU para contenção de fuga de hipervisor KVM.
- **DirtyClone e Pedit COW**: Contenção de escalada de privilégios via Copy-on-Write com `security_opt: [no-new-privileges:true]`.

### 7. Radar de cibersegurança governamental (CTIR Gov)
- O Sentinela consulta periodicamente a base oficial do GSI/CTIR Gov (`https://www.gov.br/gsi/pt-br/assuntos/ctir/alertas`).
- Grava histórico deduplicado em `logs/sentinela/ctir_alerts_seen.json`.
- Notifica imediatamente novas vulnerabilidades críticas via Telegram Bot, E-mail (SMTP/SES) e SMS (gateway SMS Legal).

---

## Instalação e execução

### No Windows:
Execute `install.bat` ou pelo PowerShell:
```powershell
.\install.ps1
```

### No Linux ou macOS:
```bash
chmod +x install.sh
./install.sh
```

### Opções do instalador:
* **[1] a [5]** Iniciar versão específica do PHP (7.4, 8.2, 8.3, 8.4 ou 8.5) com Traefik, WAF, Cronjobs, Log Collector e Honeypots.
* **[6]** Iniciar Cluster Completo (todas as versões ativas simultaneamente).
* **[7]** Iniciar Sentinela de Recursos, Antivírus ClamAV e Cronjobs.
* **[8]** Disparar varredura imediata do antivírus no código.
* **[9]** Gerar ou renovar certificados SSL locais (mkcert) e de produção.
* **[10]** Editar variáveis do arquivo `.env`.
* **[11]** Parar todos os contêineres.

---

## Endereços de acesso

* **Aplicação principal**: `http://localhost/` ou `https://localhost/`
* **Auditoria de serviços**: `http://localhost/info.php` ou `https://localhost/info.php`
* **Dashboard Traefik**: `https://localhost/load-balance/` (autenticação: `admin` / `Admin@2026`, gerenciada via `.env`)
* **Dashboard Moqesh IA**: `https://honeypot.localhost/` (login nativo: `admin` / senha do `.env`)
