# 🔒 Camada de Certificados SSL/TLS (Local e Produção)

Esta pasta gerencia todos os certificados criptográficos utilizados pelo **Traefik v2.11** para terminação TLS na porta `443`.

---

## 💻 1. Como Gerar Certificados para Ambiente LOCAL

Para desenvolvimento local com HTTPS confiável (sem aviso de "Sua conexão não é segura" no navegador), utilizamos o utilitário oficial `mkcert`.

### Opção A: Pelo Instalador Interativo (Recomendado)
Execute o instalador e escolha a opção **`[9]` (Gerar / Regenerar Certificados SSL)**:
- **Windows**: `.\install.ps1` ou clique duas vezes em `install.bat`.
- **Linux / macOS**: `./install.sh`.

### Opção B: Manualmente com mkcert
1. Instale a autoridade de certificação local no seu sistema operacional (uma única vez):
   ```bash
   mkcert -install
   ```
2. Gere os certificados apontando para os domínios locais:
   ```bash
   mkcert -cert-file ssl/certs/local-cert.pem -key-file ssl/certs/local-key.pem localhost 127.0.0.1 ::1 docker.charlescorrea.com.br *.localhost
   ```

### Opção C: Gerar via OpenSSL / Docker (Sem instalar nada no host)
Caso não queira instalar o `mkcert`, gere um certificado auto-assinado em um container descartável:
```bash
docker run --rm -v "${PWD}/ssl/certs:/certs" alpine sh -c "apk add --no-cache openssl && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/local-key.pem -out /certs/local-cert.pem -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,DNS:docker.charlescorrea.com.br,IP:127.0.0.1'"
```

---

## 🌐 2. Como Configurar Certificados em PRODUÇÃO (Let's Encrypt Automático)

Em ambiente de produção com domínio público apontado (ex: `charlescorrea.com.br`, `homologacao.charlescorrea.com.br`), o Traefik obtém e renova certificados automaticamente via protocolo ACME.

### Passo 1: Permissões do Arquivo `acme.json`
O Let's Encrypt exige que o arquivo de chaves tenha permissão estrita (`600`):
```bash
# Linux / WSL
touch ssl/letsencrypt/acme.json
chmod 600 ssl/letsencrypt/acme.json
```
*(O instalador `install.ps1` e `install.sh` já configura essa permissão automaticamente).*

### Passo 2: Configurar o Desafio ACME no `load-balance/traefik.yml`
No arquivo `load-balance/traefik.yml`, descomente e ajuste o resolvedor de certificados:
```yaml
certificatesResolvers:
  letsencryptResolver:
    acme:
      email: seu-email@charlescorrea.com.br
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web # Validação via porta 80
```

### Passo 3: Ativar o Resolvedor no `load-balance/dynamic.yml`
Nos roteadores HTTPS do `load-balance/dynamic.yml` (`router-https`), ative o certResolver:
```yaml
    router-https:
      entryPoints:
        - websecure
      rule: "Host(`charlescorrea.com.br`) || Host(`homologacao.charlescorrea.com.br`)"
      service: service-cluster-lb
      tls:
        certResolver: letsencryptResolver
```

O Traefik fará o desafio com os servidores do Let's Encrypt e renovará os certificados automaticamente a cada 60 dias sem necessidade de intervenção manual.

