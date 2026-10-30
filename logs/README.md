# 📋 Catálogo e Rotação Central de Logs (`./logs/`)

Este diretório centraliza a persistência de logs de todos os componentes da infraestrutura Docker, permitindo auditoria, investigação forense e rastreabilidade total de incidentes com retenção automática programada para **60 dias**.

---

## 📁 Estrutura de Diretórios de Logs

```text
logs/
├── antivirus/            # Logs do daemon ClamAV e atualizações de assinaturas do freshclam
├── docker/               # Coleta automática em tempo real do stdout/stderr de cada container
│   ├── app_honeypot_ia.log
│   ├── app_honeypot_robots.log
│   ├── app_waf_php83.log
│   ├── app_traefik_loadbalance.log
│   ├── app_cronjobs.log
│   ├── app_monitor.log
│   └── app_php83.log
├── sentinela/            # Histórico de telemetria, disparos de alerta e radar CTIR Gov
│   ├── alerts_YYYY-MM-DD.log      # Log diário com status de envio (Telegram, E-mail, SMS)
│   └── ctir_alerts_seen.json      # Estado persistido de comunicados do CTIR Gov já notificados
├── traefik/              # Access logs de requisições HTTP/HTTPS e eventos de roteamento
└── waf/                  # Logs de auditoria do ModSecurity CRS e bloqueios do Nginx geo $bad_ip
```

---

## ⏰ Política de Retenção e Expurgo Automático

- **Período de Retenção**: `60 dias` por padrão (customizável via `LOG_RETENTION_DAYS` no arquivo `.env`).
- **Rotina de Purga**: O serviço Sentinela (`app_monitor`) executa diariamente uma varredura recursiva por todas as subpastas de `logs/`, expurgando arquivos cujo tempo de modificação seja superior à janela de retenção.
- **Fuso Horário & Carimbos**: Todos os logs usam o fuso de Brasília (`America/Sao_Paulo`, UTC-03:00) em formato ISO ou legível brasileiro.

