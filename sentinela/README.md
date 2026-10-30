# 👁️ Sentinela Guardian & Monitoramento de Integridade

O Sentinela (`app_monitor`) é um serviço em segundo plano desenvolvido em Python responsável pela **observabilidade contínua de recursos** e **defesa de integridade do cluster**.

---

## 🚀 Principais Responsabilidades

1. **Monitoramento de Recursos do Host**:
   - Amostragem contínua a cada 60 segundos de consumo de **CPU**, **Memória RAM** e **Disco**.
   - Gatilho de alerta programável quando o consumo ultrapassar `70.0%`.
2. **Integração com o Antivírus ClamAV**:
   - Varredura de integridade da pasta compartilhada de uploads (`/scandata` mapeada em `Application/`).
   - Movimentação automática de malwares identificados para a pasta de quarentena isolada.
3. **Canais Multi-Plataforma de Notificação**:
   - **Telegram**: Mensagens instantâneas via Telegram Bot API com métricas do alerta.
   - **E-mail**: Notificações HTML estilizadas via Amazon SES / SMTP seguro.
   - **SMS**: Disparo de SMS crítico para administradores via gateway SMS Legal.

4. **Monitoramento Oficial de Cibersegurança (CTIR Gov)**:
   - Consulta contínua à base de alertas do **GSI / CTIR Gov** (`https://www.gov.br/gsi/pt-br/assuntos/ctir/alertas`).
   - Disparo imediato e deduplicado via **Telegram**, **E-mail** e **SMS Legal** a cada nova vulnerabilidade pública emitida.
   - Persistência de baseline e histórico em `logs/sentinela/ctir_alerts_seen.json`.

---

## 📁 Estrutura de Arquivos

```text
sentinela/
├── docker/          # Dockerfile com ambiente Python e dependências do Sentinela
├── emails/          # Templates HTML para e-mails de alerta (antivírus, recursos, SSL, cibersegurança)
└── monitor/         # Código-fonte principal do daemon (monitor.py e ctir_gov_checker.py)
```

