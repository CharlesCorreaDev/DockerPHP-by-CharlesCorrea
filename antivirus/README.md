# Antivírus ClamAV e quarentena

Esta camada centraliza a detecção de malware e o isolamento de arquivos suspeitos no cluster. O serviço roda no contêiner `app_clamav` com base no mecanismo open-source ClamAV (Cisco Talos).

## Repositórios e documentação oficial

* [Repositório oficial do ClamAV no GitHub](https://github.com/Cisco-Talos/clamav)
* [Documentação oficial do ClamAV](https://docs.clamav.net/)
* [Imagem oficial no Docker Hub (clamav/clamav)](https://hub.docker.com/r/clamav/clamav)
* [Base de assinaturas e base de dados Talos](https://www.clamav.net/downloads)

## O que cada componente faz

### Daemon ClamAV (`clamd`)
* **Execução**: Escuta internamente na porta TCP `3310` sob a rede isolada `cluster_network`. Não fica exposto à internet nem ao host.
* **Comunicação por socket de rede**: Permite que o Sentinela, scripts PHP e rotinas de upload enviem arquivos por stream ou caminhos montados para inspeção com comandos nativos como `PING` -> `PONG` e `INSTREAM`.

### Atualizador de assinaturas (`freshclam`)
* **Mecanismo**: Serviço em segundo plano que consulta os servidores oficiais do ClamAV para baixar novas assinaturas de vírus, cavalos de troia e exploits.
* **Persistência (`clamav_db`)**: As bases baixadas ficam salvas no volume nomeado `clamav_db`, evitando downloads redundantes a cada reinício do contêiner.

### Diretório de quarentena (`quarentena/`)
* **Finalidade**: Destino automático de qualquer artefato onde o scan aponte infecção.
* **Segurança operacional**: O diretório possui `.gitignore` dedicado para evitar commit acidental de payloads maliciosos no repositório Git, além de ter permissões de execução revogadas.

## Comandos úteis de operação

Testar a conectividade do daemon a partir da rede interna:
```bash
docker exec -it app_sentinela nc -z app_clamav 3310 && echo "ClamAV online"
```

Forçar atualização manual das assinaturas:
```bash
docker exec -it app_clamav freshclam
```

Verificar a versão e base ativa:
```bash
docker exec -it app_clamav clamdscan --version
```
