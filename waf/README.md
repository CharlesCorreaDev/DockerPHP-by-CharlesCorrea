# Camada WAF e firewall de aplicação (OWASP ModSecurity CRS e Nginx)

Esta camada realiza a inspeção profunda de pacotes nas requisições HTTP e HTTPS direcionadas à aplicação. Ela atua posicionada entre o balanceador Traefik e os servidores FrankenPHP/Apache, filtrando ameaças catalogadas no OWASP Top 10 antes que alcancem o interpretador PHP.

## Repositórios e documentação oficial

* [Repositório oficial do OWASP Core Rule Set (coreruleset/coreruleset)](https://github.com/coreruleset/coreruleset)
* [Documentação oficial do OWASP ModSecurity Core Rule Set](https://coreruleset.org/docs/)
* [Repositório oficial da imagem Docker OWASP CRS (coreruleset/modsecurity-crs-docker)](https://github.com/coreruleset/modsecurity-crs-docker)
* [Repositório oficial do ModSecurity (owasp-modsecurity/ModSecurity)](https://github.com/owasp-modsecurity/ModSecurity)
* [Documentação de módulos do servidor Nginx](https://nginx.org/en/docs/)
* [OWASP Top 10 Web Application Security Risks](https://owasp.org/www-project-top-ten/)

## O que cada componente faz

### 1. Mecanismo de inspeção ModSecurity CRS
* **Análise de entrada e saída**: Inspeciona cabeçalhos, parâmetros de URL, cookies e o corpo da requisição (`MODSEC_REQ_BODY_ACCESS=on`) e resposta (`MODSEC_RESP_BODY_ACCESS=on`).
* **Proteção contra classes de vulnerabilidade**: Bloqueia tentativas de exploração de SQL Injection (SQLi), Cross-Site Scripting (XSS), Remote Code Execution (RCE), Injeção de Comandos de Sistema, Local/Remote File Inclusion (LFI/RFI) e PHP Object Injection.
* **Modelo de pontuação de anomalia (Anomaly Scoring)**: Regras associam pontos às requisições com base na severidade da inconformidade; se a pontuação acumulada ultrapassar o limiar de entrada (`ANOMALY_INBOUND=5`), a conexão é descartada com código HTTP 403.
* **Regras de mitigação virtual**: Contém assinaturas específicas para neutralização de tentativas de exploração das vulnerabilidades CVE-2026-109618 e CVE-2026-109619.

### 2. Bloqueio por reputação de endereço (`geo $bad_ip`)
* **Consolidação de listas**: O Nginx carrega arquivos de reputação em formato IP CIDR (StopForumSpam, Spamhaus, FireHOL) e a lista dinâmica `honeypot_blocklist.txt` alimentada pelos honeypots locais.
* **Descarte imediato**: Conexões originadas de IPs presentes nessa base recebem resposta `403 Forbidden` diretamente no Nginx, sem repassar processamento ao backend PHP.

### 3. Camuflagem de software e headers enganosos
* **Headers de tecnologia**: Modifica os cabeçalhos de resposta para simular uma infraestrutura Windows Server (`Server: Microsoft-IIS/10.0` e `X-Powered-By: ASP.NET`).
* **Headers simulados de CDN**: Inclui cabeçalhos característicos de proxy de borda (`cf-ray`, `cf-cache-status`), confundindo scanners e ferramentas de enumeração de tecnologia que buscam servidores PHP e Nginx.

### 4. Mecanismos defensivos ativos
* **Redirecionamento em loop (Buraco Negro)**: Scanners automatizados que tentam localizar backups, dumps de banco (`.sql`), arquivos de configuração (`.env`, `.conf`) ou diretórios administrativos caem em rotas com redirecionamento cíclico 301.
* **Gzip Decompression Bomb**: Requisitantes identificados com comportamento hostil persistente recebem arquivos altamente comprimidos que se expandem para gigabytes caso o cliente tente descompactar na memória, esgotando os recursos da ferramenta invasora.

## Estrutura do diretório

```text
waf/
├── config/              # Regras customizadas do ModSecurity e arquivos de blocklist
├── scripts/             # Scripts de atualização periódica de listas e regras CVE
├── templates/           # Modelos de configuração do Nginx com camuflagem IIS e diretiva geo
└── errors/              # Páginas de erro customizadas do IIS e artefatos de defesa ativa
```

## Operações e comandos do WAF

Testar a sintaxe dos arquivos de configuração do Nginx dentro do contêiner WAF ativo:
```bash
docker exec -it app_waf_php83 nginx -t
```

Recarregar regras e listas de bloqueio sem encerrar conexões:
```bash
docker exec -it app_waf_php83 nginx -s reload
```

Acompanhar os logs de bloqueio do ModSecurity em tempo real:
```bash
docker logs -f app_waf_php83
```
