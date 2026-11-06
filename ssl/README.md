# Camada de certificados SSL e TLS

Este diretório armazena e gerencia os certificados digitais consumidos pelo balanceador Traefik para terminação criptográfica TLS na porta 443 (HTTPS), tanto em desenvolvimento local quanto em servidores de produção.

## Repositórios e documentação oficial

* [Repositório oficial do mkcert](https://github.com/FiloSottile/mkcert)
* [Documentação do Traefik sobre configuração de TLS](https://doc.traefik.io/traefik/https/tls/)
* [Guia do Traefik para Let's Encrypt e ACME](https://doc.traefik.io/traefik/https/acme/)
* [Documentação técnica da autoridade certificadora Let's Encrypt](https://letsencrypt.org/docs/)
* [Especificação RFC 8555 - Protocolo ACME (Automatic Certificate Management Environment)](https://datatracker.ietf.org/doc/html/rfc8555)

## O que cada componente faz

### 1. Certificados para ambiente local (`ssl/certs/`)
* **Problema atendido**: Navegadores modernos emitem alertas de conexão insegura (`NET::ERR_CERT_AUTHORITY_INVALID`) quando certificados autoassinados comuns são utilizados em `localhost`.
* **Solução com mkcert**: A ferramenta instala uma Autoridade Certificadora (CA) raiz confiável na máquina do desenvolvedor e gera certificados válidos para `localhost`, `127.0.0.1` e nomes de domínio locais.
* **Mapeamento estático (`dynamic-tls.yml`)**: O Traefik carrega os certificados através do arquivo de configuração dinâmica `ssl/certs/dynamic-tls.yml`, associando o par de chaves `local-cert.pem` e `local-key.pem` a todas as requisições que chegam pelo ponto de entrada `websecure`.

### 2. Certificados para produção com Let's Encrypt (`ssl/letsencrypt/`)
* **Mecanismo**: Utiliza o protocolo RFC 8555 (ACME) nativo do Traefik para requisição e renovação automática de certificados com validade global.
* **Arquivo de armazenamento (`acme.json`)**: Armazena as chaves privadas e os certificados emitidos. Exige permissões estritas de arquivo (`chmod 600`) para que o Traefik autorize sua leitura e escrita.
* **Métodos de validação**: Suporta os desafios `httpChallenge` (validação na porta 80) e `tlsChallenge` (desafio TLS-ALPN na porta 443).

## Métodos para geração de certificados locais

### Opção 1: Via instalador do projeto (Recomendado)
Execute o instalador e selecione a opção de geração de certificados SSL:
* **Windows**: Execute `.\install.ps1` no PowerShell ou execute `install.bat`.
* **Linux / macOS**: Execute `./install.sh`.

### Opção 2: Linha de comando com mkcert
1. Instale a autoridade certificadora raiz no sistema operacional (apenas na primeira configuração):
   ```bash
   mkcert -install
   ```
2. Gere o par de chaves no diretório esperado pelo Traefik:
   ```bash
   mkcert -cert-file ssl/certs/local-cert.pem -key-file ssl/certs/local-key.pem localhost 127.0.0.1 ::1 *.localhost
   ```

### Opção 3: Geração via contêiner efêmero Docker (Sem instalar ferramentas no host)
```bash
docker run --rm -v "${PWD}/ssl/certs:/certs" alpine sh -c "apk add --no-cache openssl && openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/local-key.pem -out /certs/local-cert.pem -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1'"
```

## Configuração para ambiente de produção

1. Assegure as permissões corretas do arquivo `acme.json`:
   ```bash
   touch ssl/letsencrypt/acme.json
   chmod 600 ssl/letsencrypt/acme.json
   ```
2. Configure o resolvedor ACME no arquivo `load-balance/traefik.yml` ou utilize o arquivo complementar `docker-compose.prod.yml`:
   ```yaml
   certificatesResolvers:
     letsencryptResolver:
       acme:
         email: admin@dominio.com.br
         storage: /letsencrypt/acme.json
         httpChallenge:
           entryPoint: web
   ```
3. No arquivo `load-balance/dynamic.yml`, vincule o resolvedor aos roteadores que atendem o domínio público:
   ```yaml
   router-https:
     entryPoints:
       - websecure
     rule: "Host(`dominio.com.br`)"
     service: service-cluster-lb
     tls:
       certResolver: letsencryptResolver
   ```
As renovações ocorrem automaticamente pelo Traefik a cada 60 dias sem exigir reinicialização do contêiner.
