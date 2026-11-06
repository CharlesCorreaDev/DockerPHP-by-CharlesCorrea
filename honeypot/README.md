# Camada de detecção ativa por honeypots

Esta camada reúne duas armadilhas de segurança complementares, roteadas pelo Traefik antes da chegada das requisições ao WAF ou aos contêineres PHP da aplicação. Todos os endereços IP capturados são gravados em uma blocklist compartilhada (`geo $bad_ip`) que os servidores Nginx carregam para bloqueio imediato com código HTTP 403 em todo o site.

Os serviços operam no fuso horário oficial de Brasília (`America/Sao_Paulo`) e contam com interface em português do Brasil (pt-BR).

## Repositórios e documentação oficial

* [Repositório oficial do Moqesh AI Honeypot (juliourena/moqesh)](https://github.com/juliourena/moqesh)
* [Documentação do módulo HTTP Geo do Nginx](https://nginx.org/en/docs/http/ngx_http_geo_module.html)
* [Conceitos de Honeytokens e Deception Technology (OWASP)](https://owasp.org/)
* [Guia de mitigação de automação maliciosa (OWASP Automated Threats to Web Applications)](https://owasp.org/www-project-automated-threats-to-web-applications/)

## O que cada componente faz

### 1. Honeypot para agentes de IA autônomos (`app_honeypot_ia`)
* **Objetivo**: Identificar bots modernos equipados com LLM, scanners automatizados de vulnerabilidades e crawlers que exploram rotas conceituais e arquivos sensíveis.
* **Rotas monitoradas pelo Traefik**: Endereços como `/.env`, `/.git`, `/.aws`, `/internal`, `/backup`, `/staging` e `/api-internal`.
* **Análise comportamental**: O Moqesh avalia intervalos de requisição, navegação estruturada e consumo de honeytokens. Quando o índice de suspeita atinge o limiar configurado (`MOQESH_AUTO_BLOCK_SCORE`), o sistema dispara um webhook assinado para o serviço bridge.
* **Interface do painel**: O dashboard do Moqesh foi traduzido para pt-BR e fica acessível em `https://honeypot.localhost/` com autenticação local administrativa.

### 2. Ponte de integração (`app_honeypot_ia_bridge`)
* **Mecanismo**: Microsserviço em Python que escuta webhooks gerados pelo Moqesh via socket interno.
* **Validação de assinatura**: Valida a chave HMAC recebida no cabeçalho contra a variável `MOQESH_WEBHOOK_SECRET` do arquivo `.env`.
* **Inclusão na blocklist**: Insere o endereço IP agressor no arquivo `blocklist/honeypot_blocklist.txt` respeitando a lista de exceções (`HONEYPOT_WHITELIST`).

### 3. Honeypot para scanners e bots tradicionais (`app_honeypot_robots`)
* **Objetivo**: Capturar scanners de CMS, ferramentas de força bruta e kits de exploração automatizados.
* **Rotas monitoradas**: Caminhos como `/wp-login.php`, `/wp-admin`, `/xmlrpc.php`, `/phpmyadmin`, `/pma`, `/adminer`, `/vendor/phpunit`, `/cgi-bin`, arquivos de shell (`.php`) e rotas isca como `/robots-trap`.
* **Mecanismo Tarpit**: Prende a conexão do bot enviando bytes lentamente para consumir os sockets e a memória do cliente invasor.
* **Limite de infrações**: Após atingir o número máximo de acessos suspeitos (`ROBOTS_BLOCK_THRESHOLD`), o IP entra para a blocklist do cluster. Em acessos reincidentes (`hits >= 4`), o serviço redireciona o tráfego para resposta externa educativa.

### 4. Integração de iscas no código da aplicação (`lures/`)
* **`IA/lures/robots.txt`**: Define caminhos proibidos direcionados aos honeypots para induzir bots rastreadores à violação de rotas.
* **`IA/lures/honeypot-lures.php`**: Injeta links HTML com estilo de exibição oculto para visitantes humanos, mas visíveis no DOM para spiders de extração.
* **`Robots/php/HoneypotField.php`**: Adiciona campos invisíveis em formulários de contato e login; robôs que preenchem esses campos são classificados como atacantes.

## Estrutura do diretório

```text
honeypot/
├── IA/                      # Armadilha focada em agentes e modelos de linguagem
│   ├── moqesh/              # Repositório clonado e customizado com tradução pt-BR
│   ├── Dockerfile.moqesh    # Build customizado com fuso horário e localização
│   ├── bridge/              # Serviço receptor de webhooks e manipulador de regras
│   └── lures/               # Iscas sintéticas para inclusão em robots.txt e layouts
├── Robots/                  # Armadilha para bots convencionais e scanners de portas
│   ├── robots_honeypot.py   # Script do servidor tarpit e emulação de endpoints
│   └── php/HoneypotField.php# Helper de inclusão de campos em formulários PHP
├── blocklist/
│   └── honeypot_blocklist.txt # Lista de endereços no formato "IP 1;" para o Nginx
└── scripts/
    └── reload_waf_blocklist.sh# Script de recarga suave nas instâncias do WAF
```

## Operação e desbloqueio de endereços

Para forçar a recarga imediata da lista de bloqueio nos WAFs sem aguardar o agendador:
```bash
docker exec app_waf_php83 sh /scripts/reload_waf_blocklist.sh
```

Para remover o bloqueio de um endereço capturado por engano:
1. Abra o arquivo `honeypot/blocklist/honeypot_blocklist.txt`.
2. Remova a linha correspondente ao endereço IP.
3. Execute o comando de recarga do WAF acima.
4. Caso o IP seja fixo e administrativo, adicione sua máscara na variável `HONEYPOT_WHITELIST` no arquivo `.env`.
