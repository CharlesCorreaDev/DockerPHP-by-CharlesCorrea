# Imagens de runtime PHP e coletor de logs

Este diretório contém as definições de compilação dos ambientes de execução PHP (versões 7.4, 8.2, 8.3, 8.4 e 8.5) e o serviço coletor contínuo de logs dos contêineres Docker.

## Repositórios e documentação oficial

* [Repositório oficial do FrankenPHP](https://github.com/dunglas/frankenphp)
* [Repositório oficial do instalador de extensões PHP (mlocati/docker-php-extension-installer)](https://github.com/mlocati/docker-php-extension-installer)
* [Repositório oficial das imagens Docker PHP](https://github.com/docker-library/php)
* [Documentação de segurança e isolamento de contêineres Docker](https://docs.docker.com/engine/security/)
* [Especificação da API de logs do Docker Engine](https://docs.docker.com/engine/api/v1.44/#tag/Container/operation/ContainerLogs)

## O que cada componente faz

### Imagens FrankenPHP (PHP 8.2, 8.3, 8.4 e 8.5)
* **Base do sistema**: Construídas sobre imagens oficiais do FrankenPHP com Alpine Linux ou Debian Slim para redução da superfície de ataque e tamanho de imagem.
* **Worker Mode**: O interpretador PHP e os arquivos da aplicação são carregados na memória de forma permanente, atendendo requisições com latência reduzida.
* **Módulos compilados**: Incluem OPcache com compilação JIT ativada, drivers de banco de dados (PDO MySQL, PostgreSQL, SQLite), Redis para cache distribuído, processamento de imagens (GD/Imagick) e bibliotecas de compressão.
* **Isolamento de privilégios**: Os processos rodam com usuário dedicado não privilegiado (`www-data`) e com a restrição de elevação de privilégios (`no-new-privileges:true`).

### Imagem PHP 7.4 (Compatibilidade legado)
* **Finalidade**: Oferecer suporte para sistemas legados que exigem sintaxe e extensões incompatíveis com o PHP 8+.
* **Servidor**: Baseado em Apache com `mod_php`, isolado em sua própria rede interna e protegido por seu respectivo contêiner WAF dedicado (`app_waf_php74`).

### Coletor contínuo de logs (`app_log_collector`)
* **Mecanismo**: Serviço em Python que consome o socket do Docker (`/var/run/docker.sock`) em modo streaming contínuo.
* **Persistência**: Captura as saídas padrão (`stdout`) e de erro (`stderr`) de cada contêiner em tempo real, gravando os dados em arquivos individuais no caminho `logs/docker/<container_name>.log`.
* **Padronização temporal**: Aplica formatação de carimbos de data e hora no fuso horário oficial de Brasília (`America/Sao_Paulo`, UTC-3), facilitando a correlação de incidentes com os registros do WAF e do Traefik.

## Estrutura do diretório

```text
docker/
├── log-collector/        # Script Python e Dockerfile do coletor contínuo de logs
├── php7.4/               # Dockerfile do ambiente legado PHP 7.4 Apache
├── php8.2/               # Dockerfile do FrankenPHP Worker com PHP 8.2
├── php8.3/               # Dockerfile do FrankenPHP Worker com PHP 8.3
├── php8.4/               # Dockerfile do FrankenPHP Worker com PHP 8.4
└── php8.5/               # Dockerfile do FrankenPHP Worker com PHP 8.5
```
