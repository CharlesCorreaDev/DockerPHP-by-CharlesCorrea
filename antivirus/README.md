# 🦠 Antivírus ClamAV & Quarentena

Esta camada provê o serviço de detecção e contenção de malwares em tempo real via **ClamAV Daemon (`clamd`)** rodando no container `app_clamav`.

---

## ⚙️ Arquitetura de Proteção

- **Porta Interna `3310`**: O daemon escuta exclusivamente na rede interna do cluster (`cluster_network`), respondendo a comandos padrão como `PING` -> `PONG` e escaneamentos via protocolo clamd.
- **Assinaturas Virais Atualizadas**: O processo `freshclam` atualiza periodicamente as bases globais de assinaturas de vírus e malwares persistidas no volume `clamav_db`.
- **Isolamento em Quarentena (`quarentena/`)**:
  - Arquivos infectados detectados pelo Sentinela ou scripts da aplicação são automaticamente movidos para a pasta de quarentena.
  - A pasta possui permissões restritas e exclusão no `.gitignore` para impedir que arquivos maliciosos sejam versionados ou executados.

