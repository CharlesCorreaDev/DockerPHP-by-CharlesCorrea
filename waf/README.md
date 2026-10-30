# 🧱 Camada WAF & Firewall de Aplicação (OWASP ModSecurity CRS + Nginx)

Esta camada atua como a **muralha de inspeção profunda de pacotes HTTP/HTTPS**, mitigando ataques web do OWASP Top 10 antes que a requisição seja entregue aos interpretadores PHP.

---

## 🛡️ Funcionalidades e Mecanismos Defensivos

1. **OWASP Core Rule Set (CRS) v3 / ModSecurity**:
   - Inspeção rigorosa de corpo (`REQ_BODY_ACCESS=on`) e resposta (`RESP_BODY_ACCESS=on`).
   - Bloqueio imediato de **SQL Injection**, **Cross-Site Scripting (XSS)**, **Remote Code Execution (RCE)** e **PHP Object Injection**.
2. **Mitigação Virtual de Vulnerabilidades**:
   - Regras virtuais de bloqueio imediato contra explorações `CVE-2026-109618` e `CVE-2026-109619`.
3. **Mapeamento de Ameaças em Tempo Real (`geo $bad_ip`)**:
   - Carrega `stopforumspam.txt` e a blocklist consolidada `honeypot_blocklist.txt` (alimentada pelas capturas dos Honeypots).
   - Invasores identificados recebem `HTTP 403 Forbidden` instantâneo sem onerar o PHP.
4. **Camuflagem Microsoft-IIS/10.0 & Cloudflare**:
   - Responde com headers idênticos ao IIS (`Server: Microsoft-IIS/10.0`, `X-Powered-By: ASP.NET`) e headers Cloudflare (`cf-ray`, `cf-cache-status`), desorientando scanners automatizados.
5. **Gzip Decompression Bomb & Buraco Negro (Loop 301)**:
   - Scanners buscando extensões críticas (`.sql`, `.bak`, `.conf`) caem em loop de redirecionamento ou recebem arquivo de descompressão massiva.

---

## 📁 Estrutura de Arquivos

```text
waf/
├── config/              # Overrides ModSecurity e listas de reputação de IP
├── scripts/             # Scripts de atualização automática de blocklists e CVEs
├── templates/           # Templates Nginx com camuflagem IIS/Cloudflare e geo $bad_ip
└── errors/              # Páginas de erro customizadas do IIS e gzip bomb
```

