# Camada de aplicação PHP e FrankenPHP

Este diretório contém o código-fonte da aplicação web e os pontos de entrada para o servidor de aplicação FrankenPHP.

## Repositórios e documentação oficial

* [Repositório oficial do FrankenPHP](https://github.com/dunglas/frankenphp)
* [Documentação oficial do FrankenPHP](https://frankenphp.dev/)
* [Documentação oficial do PHP](https://www.php.net/docs.php)
* [Documentação do servidor Caddy](https://caddyserver.com/docs/)
* [Guia oficial do Composer](https://getcomposer.org/doc/)

## O que cada componente faz

### Servidor de aplicação FrankenPHP
* **Arquitetura híbrida**: O FrankenPHP integra o interpretador PHP diretamente no servidor web Caddy usando a biblioteca Go `cgo`.
* **Worker Mode (`frankenphp-worker.php`)**: Carrega o framework e o código da aplicação uma única vez na memória RAM. As requisições seguintes são atendidas sem o overhead de inicialização de processos do modelo tradicional PHP-FPM.
* **Controle de ciclo de vida e memória**: Cada worker executa rotinas periódicas de coleta de lixo (`gc_collect_cycles()`) e é reciclado após um limite seguro de requisições (`MAX_REQUESTS=1000`), evitando fragmentação ou vazamentos de memória.

### Identificação dinâmica de ambiente
O arquivo `frankenphp-worker.php` inspeciona o cabeçalho `Host` de cada requisição e categoriza o contexto operacional caso a variável `APP_ENV` não esteja prefixada no arquivo `.env`:
* **Ambiente local**: Ativado para conexões em `localhost`, `127.0.0.1`, `::1` ou domínios terminados em `.localhost`.
* **Ambiente de homologação**: Identificado por prefixos como `homologacao.*`, `staging.*` ou `hml.*`.
* **Ambiente de produção**: Configurado para domínios públicos oficiais e endereços externos.

### Painel de diagnóstico do cluster (`info.php`)
Localizado em `http://localhost/info.php` ou `https://localhost/info.php`:
* **Auditoria de serviços**: Realiza verificações de conectividade e integridade nos serviços da infraestrutura (WAF ModSecurity, Antivírus ClamAV, Honeypot Moqesh IA, Honeypot Robots, Traefik Load Balancer, Sentinela e certificados SSL).
* **Checagem de vulnerabilidades**: Verifica conformidade contra as mitigações do CVE-2026-109618 e CVE-2026-109619 no runtime.
* **Parâmetros de execução**: Exibe diretivas ativas do `php.ini`, memória alocada, limites de upload e extensões carregadas.

## Estrutura de arquivos do diretório

* `index.php`: Ponto de entrada padrão para requisições em modo clássico ou rotas de teste.
* `info.php`: Dashboard analítico de integridade da infraestrutura e dos módulos PHP.
* `frankenphp-worker.php`: Script de controle para execução contínua em modo Worker.
* `composer.json`: Definição de dependências e mapeamento de autoload PSR-4 do projeto.
