# ⏰ Camada de Automação & Cronjobs (Master-Cron)

O serviço `app_cronjobs` é um orquestrador conteinerizado autônomo baseado em Python responsável por disparar tarefas de manutenção periódicas, rotação de logs e atualização de inteligência de ameaças no cluster.

---

## ⚙️ Como Funciona o Orquestrador

- O container monta o `/var/run/docker.sock` em modo de somente leitura (`:ro`).
- Lê o arquivo de declaração de tarefas em `Jobs/tasks/tasks.json`.
- A cada intervalo programado (`schedule_hours`), localiza os containers alvo pelo padrão de nome (`target_container_pattern`) e executa o script desejado via `c.exec_run()`.

---

## 📋 Tarefas Ativas em `tasks.json`

1. **`waf-blocklist-update` (a cada 12h)**:
   - Executa `/scripts/update_blocklist.sh` nos containers WAF Nginx.
   - Baixa e consolida feeds de Threat Intelligence (StopForumSpam, Spamhaus DROP/EDROP, FireHOL Level 1 e AbuseIPDB).
2. **`waf-report-spam` (a cada 1h)**:
   - Executa `/scripts/report_spam.sh` para reporte de atacantes capturados no honeypot para serviços globais de reputação.
3. **`honeypot-blocklist-reload` (a cada 1h)**:
   - Executa `/scripts/reload_waf_blocklist.sh` nos containers WAF.
   - Aplica os IPs capturados em tempo real pelos honeypots (IA Moqesh e Robots) na diretiva `geo $bad_ip` do Nginx com reload suave (`nginx -s reload`).

---

## 📁 Estrutura de Arquivos

```text
Cronjobs/
├── Dockerfile           # Imagem base Python com biblioteca docker-py
├── Jobs/tasks/          # Configuração de agendamento (tasks.json)
├── Master-Cron/         # Script principal do daemon (master_scheduler.py)
└── Scripts/             # Scripts adicionais de manutenção do cluster
```

