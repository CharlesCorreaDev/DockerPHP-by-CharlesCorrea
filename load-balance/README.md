# Camada de borda e balanceamento de carga (Traefik v2.11)

Esta camada funciona como o gateway de entrada do cluster nas portas 80 (HTTP) e 443 (HTTPS). Ela centraliza a terminação TLS, a distribuição de tráfego, a execução de plugins de segurança e a triagem antecipada de rotas sensíveis antes do repasse aos contêineres de WAF e aplicação.

## Repositórios e documentação oficial

* [Repositório oficial do Traefik no GitHub (traefik/traefik)](https://github.com/traefik/traefik)
* [Documentação oficial do Traefik v2](https://doc.traefik.io/traefik/v2.11/)
* [Catálogo oficial de Plugins do Traefik Pilot / Hub](https://plugins.traefik.io/)
* [Plugin traefik-real-ip](https://plugins.traefik.io/plugins/628efc0e5a96306e12e1045e/traefik-real-ip)
* [Plugin bad-bot-blocker](https://plugins.traefik.io/plugins/62dc052b610c14b2160d5b6d/bad-bot-blocker)
* [Plugin torblock](https://plugins.traefik.io/plugins/6297bc9165b4c1aa5718df2b/torblock)

## O que cada componente faz

### Configuração estática (`traefik.yml`)
* **Pontos de entrada (EntryPoints)**: Inicializa as portas 80 (`web`) e 443 (`websecure`).
* **Resolução de certificados ACME**: Gerencia a integração com a autoridade certificadora Let's Encrypt quando operando com o arquivo de produção `docker-compose.prod.yml`.
* **Provedores de configuração**: Monitora o provedor de arquivos (`file provider`) apontando para `dynamic.yml` e o provedor do Docker via `/var/run/docker.sock`.
* **Registro de métricas e logs**: Grava eventos de acesso e depuração com rotação em `logs/traefik/`.

### Configuração dinâmica e prioridades (`dynamic.yml`)
O Traefik aplica um modelo rigoroso de prioridades para evitar que varreduras atinjam os servidores de backend:
* **Prioridade 9000 (Interceptação de honeypot)**: Captura requisições para caminhos de reconhecimento (`/.env`, `/.git`, `/internal`, `/wp-login.php`, etc.) e desvia para os contêineres de armadilha sem acionar a aplicação.
* **Prioridade 2000 (Healthcheck estático na borda)**: As rotas `/healthz` e `/ping` respondem código 200 diretamente pela memória do Traefik através do middleware `staticresponse`, economizando ciclos de CPU dos backends.
* **Prioridade 1500 (Dashboard do Moqesh IA)**: Expõe a interface analítica do Moqesh no endereço `https://honeypot.localhost/`.
* **Prioridade 1000 (Dashboard Traefik)**: Acessível na rota `https://localhost/load-balance/` protegida por autenticação HTTP Basic Auth configurada pelas variáveis do arquivo `.env`.
* **Prioridade 100 (Tráfego de aplicação)**: Encaminha os acessos legítimos para a instância do WAF ModSecurity correspondente à versão PHP selecionada.

### Cadeia de middlewares de segurança da borda
1. **`mw-real-ip`**: Inspeciona cabeçalhos `CF-Connecting-IP`, `X-Forwarded-For` e `X-Real-IP`, redefinindo o endereço real de origem do cliente antes de repassar a requisição aos componentes internos.
2. **`mw-request-id`**: Gera um identificador único de correlação (UUID) por requisição no cabeçalho `X-Request-ID`.
3. **`mw-bad-bot-blocker`**: Descarta requisições com User-Agents associados a ferramentas conhecidas de varredura ou bibliotecas de raspagem abusiva.
4. **`mw-tor-block`**: Compara o IP de origem contra a lista pública de nós de saída da rede Tor e bloqueia o tráfego anônimo.
5. **`mw-validate-headers`**: Exige a presença de cabeçalhos mínimos obrigatórios para evitar tráfego malformado.
6. **`mw-cors-preflight`**: Trata requisições OPTIONS com código HTTP 204 na própria camada de borda.
7. **`mw-buffering`**: Impede ataques de esgotamento de buffer limitando o tamanho dos payloads de requisição e resposta a 15 MB.
8. **`mw-security-headers`**: Aplica regras estritas de HSTS (31536000s com subdomínios), Content Security Policy (CSP), Cross-Origin Embedder/Opener Policy e camufla as assinaturas do servidor com valores sintéticos (`Server: Microsoft-IIS/10.0` e `X-Powered-By: ASP.NET`).

## Estrutura do diretório

```text
load-balance/
├── traefik.yml      # Configuração de inicialização estática e registro de plugins
├── dynamic.yml      # Roteamento dinâmico, cadeias de middlewares e serviços
└── cache/           # Armazenamento temporário do cache de borda
```
