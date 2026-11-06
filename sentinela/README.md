# Camada de observabilidade e integridade (Sentinela)

O serviço Sentinela (`app_monitor`) é um daemon desenvolvido em Python responsável pela monitoração contínua de recursos do sistema, verificação de integridade de arquivos em conjunto com o antivírus ClamAV, despacho de alertas multicanal e acompanhamento de boletins oficiais de cibersegurança do governo brasileiro.

## Repositórios e documentação oficial

* [Repositório da biblioteca psutil em Python](https://github.com/giampaolo/psutil)
* [Documentação oficial do psutil](https://psutil.readthedocs.io/)
* [Documentação da API de bots do Telegram](https://core.telegram.org/bots/api)
* [Portal do CTIR Gov Brasil (GSI/PR)](https://www.gov.br/ctir/pt-br)
* [Documentação da API de envio SMS Legal](https://smslegal.com.br/)
* [Guia do módulo smtplib do Python](https://docs.python.org/3/library/smtplib.html)

## O que cada componente faz

### 1. Monitor de recursos de hardware
* **Coleta de métricas**: A cada 60 segundos, consulta métricas de utilização de CPU, memória RAM e armazenamento em disco através da biblioteca `psutil`.
* **Disparo por limiar**: Quando a utilização de qualquer um desses recursos ultrapassa o limite padrão (70% ou valor definido no `.env`), o Sentinela registra o evento e dispara mensagens de alerta aos administradores.

### 2. Integração com o antivírus ClamAV
* **Inspeção de uploads**: O daemon monitora o diretório de dados `/scandata` (mapeado para `Application/`) e submete arquivos ao socket do ClamAV (`app_clamav:3310`).
* **Tratamento de infecções**: Se um arquivo for classificado como infectado, o Sentinela move o artefato imediatamente para o diretório isolado de quarentena e emite notificações detalhadas contendo o nome da ameaça identificada.

### 3. Central multicanal de notificações
O Sentinela implementa três canais independentes de comunicação para garantir que falhas e ameaças cheguem à equipe:
* **Telegram**: Envio direto para os identificadores cadastrados em `TELEGRAM_CHAT_ID` via API de bots.
* **E-mail corporativo**: Envio de mensagens formatadas com templates HTML localizados em `sentinela/emails/` via SMTP autenticado ou Amazon SES.
* **SMS crítico**: Envio de mensagens de texto SMS para os números configurados no `.env` utilizando a API da SMS Legal.

### 4. Monitor de ameaças do CTIR Gov (`ctir_gov_checker.py`)
* **Acompanhamento ativo**: Consulta periodicamente o portal do Centro de Prevenção, Tratamento e Resposta a Incidentes Cibernéticos de Governo (CTIR Gov / GSI).
* **Prevenção de duplicidade**: Armazena o hash e a identificação dos boletins processados no arquivo `logs/sentinela/ctir_alerts_seen.json`.
* **Notificação antecipada**: Notifica a equipe imediatamente assim que um novo alerta de vulnerabilidade zero-day ou campanha maliciosa é publicado pelo órgão oficial brasileiro.

## Estrutura do diretório

```text
sentinela/
├── docker/          # Dockerfile do serviço em Python com bibliotecas de sistema
├── emails/          # Templates HTML para notificações (recursos, antivírus, SSL e cibersegurança)
└── monitor/         # Código-fonte do daemon (monitor.py e ctir_gov_checker.py)
```
