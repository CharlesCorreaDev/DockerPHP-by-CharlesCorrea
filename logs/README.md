# Central de registros e rotação de logs

Este diretório centraliza os registros de eventos gerados pelos contêineres e serviços da infraestrutura. A persistência em disco viabiliza auditorias de segurança, rastreamento forense de incidentes e acompanhamento da saúde dos serviços.

## Repositórios e documentação oficial

* [Documentação de drivers de logging do Docker](https://docs.docker.com/config/containers/logging/)
* [Especificação de Access Logs do Traefik](https://doc.traefik.io/traefik/observability/access-logs/)
* [Guia de formato e auditoria de logs do OWASP ModSecurity](https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-(v2.x)#secstatusengine)
* [Padrão internacional de carimbos de data/hora ISO 8601](https://www.iso.org/iso-8601-date-and-time-format.html)
* [Base de dados IANA de fusos horários (America/Sao_Paulo)](https://www.iana.org/time-zones)

## O que cada diretório de log armazena

### `logs/antivirus/`
* **Conteúdo**: Registros operacionais do antivírus ClamAV.
* **Detalhes**: Grava o histórico de download de novas bases de vírus executado pelo `freshclam` e o resultado de varreduras em lote realizadas pelo daemon `clamd`.

### `logs/docker/`
* **Conteúdo**: Saída padrão (`stdout`) e de erro (`stderr`) capturada continuamente pelo serviço `app_log_collector` via Docker Socket.
* **Arquivos**: Cada contêiner possui seu arquivo dedicado (exemplo: `app_waf_php83.log`, `app_honeypot_ia.log`, `app_traefik_loadbalance.log`).
* **Formatos**: Eventos gerados pelos serviços com carimbo de tempo normalizado em UTC-3.

### `logs/sentinela/`
* **Conteúdo**: Dados de telemetria do cluster e registros de notificações.
* **`alerts_YYYY-MM-DD.log`**: Registros diários com o status de entrega dos alertas para cada canal integrado (Telegram Bot API, SMTP e gateways SMS).
* **`ctir_alerts_seen.json`**: Base de estado que armazena os identificadores e hashes de boletins do CTIR Gov para evitar envios repetidos de alertas.

### `logs/traefik/`
* **Conteúdo**: Access logs de requisições HTTP e HTTPS atendidas pelo Traefik na borda.
* **Detalhes**: Registra IP de origem, cabeçalhos, rotas acessadas, status HTTP retornado, tempo de resposta e roteador acionado.

### `logs/waf/`
* **Conteúdo**: Logs de bloqueio gerados pelas regras do ModSecurity Core Rule Set e diretivas de IP do Nginx (`geo $bad_ip`).
* **Detalhes**: Registra regras ativadas, pontuação de anomalia acumulada, payload bloqueado e motivo da rejeição da requisição.

## Política de retenção e limpeza automática

* **Tempo de retenção padrão**: 60 dias (definido na variável `LOG_RETENTION_DAYS` no arquivo `.env`).
* **Expurgo automático**: O contêiner `app_monitor` (Sentinela) roda diariamente uma verificação recursiva nas pastas de logs, removendo com segurança arquivos com data de modificação superior ao limite configurado.
* **Fuso horário padronizado**: Todos os serviços operam configurados no fuso horário oficial de Brasília (`America/Sao_Paulo`), permitindo cruzamento direto de dados entre logs de borda, WAF, honeypot e aplicação.
