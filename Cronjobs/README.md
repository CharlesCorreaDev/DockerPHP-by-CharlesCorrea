# Camada de automação e tarefas agendadas (Cronjobs)

O serviço `app_cronjobs` é um agendador conteinerizado desenvolvido em Python. Ele gerencia rotinas periódicas de manutenção, rotação de registros e sincronização de feeds de inteligência de ameaças entre os serviços do cluster.

## Repositórios e documentação oficial

* [Repositório oficial da biblioteca Docker SDK para Python (docker-py)](https://github.com/docker/docker-py)
* [Documentação do Docker SDK para Python](https://docker-py.readthedocs.io/)
* [Documentação do módulo sched e threading em Python](https://docs.python.org/3/library/sched.html)
* [Repositório oficial do FireHOL IP Lists](https://github.com/firehol/blocklist-ipsets)
* [Portal oficial do CTIR Gov Brasil (Centro de Prevenção, Tratamento e Resposta a Incidentes Cibernéticos de Governo)](https://www.gov.br/ctir/pt-br)

## O que cada componente faz

### Agendador mestre (`master_scheduler.py`)
* **Acesso ao Docker Engine**: O contêiner monta o socket `/var/run/docker.sock` em modo leitura (`:ro`).
* **Resolução de contêineres**: Faz a leitura declarativa do arquivo `Jobs/tasks/tasks.json`, identifica os serviços em execução correspondentes ao padrão definido (`target_container_pattern`) e executa comandos diretamente com a API `exec_run()`.

### Rotinas ativas em `tasks.json`

#### 1. Sincronização de blocklists (`waf-blocklist-update`)
* **Periodicidade**: A cada 12 horas.
* **Operação**: Executa o script `/scripts/update_blocklist.sh` nos contêineres WAF.
* **Fontes consultadas**: Consolida listas de reputação de IP (StopForumSpam, Spamhaus DROP/EDROP, FireHOL Level 1 e AbuseIPDB) em tabelas de bloqueio consumidas pelo Nginx.

#### 2. Notificação e reporte de ataques (`waf-report-spam`)
* **Periodicidade**: A cada 1 hora.
* **Operação**: Executa o script `/scripts/report_spam.sh` para envio automático de relatórios de atacantes persistentes capturados nos honeypots.

#### 3. Recarga de regras dos honeypots (`honeypot-blocklist-reload`)
* **Periodicidade**: A cada 1 hora.
* **Operação**: Executa `/scripts/reload_waf_blocklist.sh` nos contêineres WAF.
* **Efeito**: Incorpora as listas dinâmicas geradas pelos honeypots (Moqesh IA e Robots) na tabela `geo $bad_ip` do Nginx e aplica a alteração via `nginx -s reload` sem derrubar conexões ativas.

#### 4. Monitoramento do CTIR Gov (`ctir-gov-alert-check`)
* **Periodicidade**: A cada 2 horas.
* **Operação**: Executa o coletor `ctir_gov_checker.py` no contêiner do Sentinela (`app_monitor`).
* **Efeito**: Realiza varredura nos alertas e comunicados oficiais do CTIR Gov (GSI/PR). Ao identificar um novo boletim de segurança, gera logs e notifica os administradores via Telegram, e-mail e SMS com controle de duplicidade por hash de postagem.

## Estrutura do diretório

```text
Cronjobs/
├── Dockerfile           # Imagem base Python com dependências docker-py
├── Jobs/tasks/          # Arquivo descritivo tasks.json com agendamentos e comandos
├── Master-Cron/         # Script principal do serviço (master_scheduler.py)
└── Scripts/             # Scripts utilitários de manutenção do cluster
```
