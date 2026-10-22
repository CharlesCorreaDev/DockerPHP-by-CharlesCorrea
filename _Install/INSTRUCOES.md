# Guia de Instalação e Manutenção

Este diretório (`_Install`) contém utilitários para facilitar a inicialização e a administração do projeto Docker 8.5, evitando que você precise decorar ou digitar comandos longos do Docker.

## 📋 Pré-requisitos
Certifique-se de que a sua máquina possui os seguintes softwares instalados:
- **Docker** (Docker Desktop no Windows/Mac ou Docker Engine no Linux)
- **Docker Compose** (Já incluso nas versões recentes do Docker Desktop)
- **mkcert** *(Opcional, para gerar certificados locais com cadeado verde no navegador)*

---

## 🔒 Arquitetura de Certificados SSL (Desenvolvimento vs. Produção)

O projeto está arquitetado para resolver o problema clássico de SSL entre máquinas locais e servidores públicos:

### 1. Ambiente Local / Desenvolvimento (`localhost`)
- Por padrão, o Let's Encrypt **não funciona** para `localhost` nem para domínios sem DNS público apontado.
- Para evitar a tela de erro `NET::ERR_CERT_AUTHORITY_INVALID`, o ambiente local utiliza a pasta `./certs` montada no Traefik com certificados gerados pela ferramenta `mkcert`.
- Com isso, você acessa **`https://localhost`** com cadeado verde seguro nativo no Chrome/Edge/Firefox sem nenhum aviso.
- Para gerar ou renovar os certificados locais a qualquer momento, basta usar a opção **21 (`ssl-generate`)** no gerenciador.

### 2. Ambiente de Produção 
- Em produção na nuvem (VPS, Azure, AWS, DigitalOcean), o servidor utiliza o arquivo complementar `docker-compose.prod.yml`.
- Esse arquivo ativa o **Let's Encrypt (ACME TLS-ALPN)** oficial no Traefik e gera o certificado válido de forma automática.
- Para subir em produção com Let's Encrypt ativo, basta usar a opção **2 (`start-prod`)** no gerenciador.

> **⚠️ Importante para Produção:** O domínio configurado na variável `DOMAIN` no arquivo `.env` deve obrigatoriamente possuir um apontamento **DNS (Registro tipo A)** apontando para o IP público do servidor antes de subir a pilha com `start-prod`.

---

## 🚀 Como Usar os Scripts

Dependendo do seu Sistema Operacional, você usará um dos arquivos na pasta `_Install`:

- **Para Windows:** `manager.bat`
- **Para Linux/Mac:** `manager.sh` (Antes de usar pela primeira vez, dê permissão de execução: `chmod +x manager.sh`)

### Modo Interativo (Mais Fácil)
Apenas dê **dois cliques** sobre o arquivo (ou execute no terminal sem nenhum parâmetro). Um menu de opções vai aparecer, basta digitar o número da ação que você deseja realizar.

### Modo Comando (Via Terminal)
Se preferir, você pode chamar os scripts passando a ação que deseja executar:

**No Windows:**
```cmd
cd _Install
manager.bat start
```

**No Linux/Mac:**
```bash
./_Install/manager.sh start
```

---

## 🛠️ Comandos Disponíveis no Gerenciador

### 🏁 Execução do Projeto
- **1. Iniciar localmente (`start`)**: Sobe a pilha padrão com certificados locais confiáveis via `docker compose up -d`. Ideal para o dia a dia de desenvolvimento em `https://localhost`.
- **2. Iniciar em Produção (`start-prod`)**: Roda `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`, ligando a emissão e renovação automática de certificados Let's Encrypt para o domínio de produção.
- **3. Parar o projeto (`stop`)**: Roda `docker compose down`. Desliga os contêineres e limpa a rede padrão deles.
- **4. Reiniciar o projeto (`restart`)**: Equivalente a realizar o "stop" e depois o "start" logo em seguida.
- **5. Reconstruir as imagens (`build`)**: Roda `docker compose build`. Ideal para quando você modificar o `Dockerfile` ou mudar a configuração do `nginx/caddy`.
- **6. Ver logs em tempo real (`logs`)**: Exibe os logs de todos os contêineres na sua tela em tempo real (`docker compose logs -f`). Para sair, aperte `Ctrl + C`.
- **7. Acessar o terminal interativo (`shell`)**: Entra na linha de comando interativa (bash/sh) dentro do contêiner PHP da aplicação.

### 📦 Dependências e Frontend
- **8. Instalar dependências (`install-deps`)**: Executa `composer install` e `npm install` automaticamente dentro do contêiner para baixar as dependências do back-end e front-end.
- **9. Atualizar dependências (`update-deps`)**: Executa `composer update` e `npm update` para atualizar as versões dos pacotes.
- **10. Rodar NPM Dev / Vite (`npm-dev`)**: Inicia o servidor de desenvolvimento do Vite (`npm run dev`) rodando dentro do contêiner.
- **11. Build de produção NPM (`npm-build`)**: Compila os assets frontend do Svelte/Vite para produção (`npm run build`).
- **12. Atualizar contêineres sem cache (`update-docker`)**: Executa uma reconstrução limpa, sem utilizar cache (`docker compose build --no-cache`), garantindo que novas dependências e imagens sejam baixadas antes de subir novamente.
- **13. Recarregar Autoload do Composer (`dump-autoload`)**: Recarrega o mapa de classes do back-end (`composer dump-autoload`), útil ao adicionar/remover novos arquivos estruturais sem rodar um update completo.
- **14. SUPER LIMPEZA de Caches (`clear-all-caches`)**: Dispara a limpeza máxima do projeto, removendo os caches de pacote do Composer, o cache global do NPM, cache local do Vite e expurgando as antigas camadas de cache do sistema builder do Docker.

### 🛡️ Firewall WAF (Nginx + Coraza)
- **15. Ver logs isolados do WAF (`waf-logs`)**: Exibe os acessos e bloqueios do Nginx/WAF em tempo real (`docker compose logs -f waf`).
- **16. Acessar o terminal do WAF (`waf-shell`)**: Entra na linha de comando interativa (sh) dentro do contêiner do Nginx. Útil para verificar configurações de bloqueio geradas.
- **17. Testar configuração do Nginx/WAF (`waf-test`)**: Checa a sintaxe dos arquivos de configuração do Nginx antes de recarregar o serviço (`nginx -t`).
- **18. Recarregar WAF sem derrubar conexões (`waf-reload`)**: Aplica novas regras de Nginx sem precisar reiniciar o contêiner e sem interromper os usuários conectados (`nginx -s reload`).

### ⚡ FrankenPHP, PHP JIT e Profilers
- **19. Reiniciar Rápido do FrankenPHP/PHP (`app-restart`)**: Reinicia instantaneamente apenas o contêiner do PHP. Essencial para recarregar alterações de código pesado no modo Worker, sem afetar o Nginx.
- **20. Recarregar config do FrankenPHP/Caddy (`frankenphp-reload`)**: Faz o reload a quente do Caddyfile e configurações nativas do FrankenPHP, preservando as conexões ativas.
- **21. Ativar PHP JIT (`jit-enable`)**: Descarrega e desativa extensões de profiling (Xdebug, SPX, XHProf, Excimer) para liberar o compilador nativo JIT com máximo desempenho.
- **22. Desativar PHP JIT (`jit-disable`)**: Reativa extensões de depuração e profiling (Xdebug/SPX/XHProf/Excimer) para desenvolvimento e análise de código.
- **23. Verificar Status do PHP JIT (`jit-status`)**: Inspeciona em tempo real o status de compilação, buffer e otimizações ativas do JIT na CPU.

### 🔒 Certificados SSL e Antivírus ClamAV
- **24. Gerar/Regenerar Certificados Locais (`ssl-generate`)**: Usa a ferramenta `mkcert` para gerar par de chaves SSL na pasta `certs/` e recarregar o balanceador Traefik com suporte local a `localhost` e `127.0.0.1`.
- **25. Executar Varredura Imediata do Antivírus (`clamav-scan`)**: Dispara scan imediato de malwares em `/scandata` (código da aplicação) através do daemon ClamAV com isolamento automático para quarentena.
- **26. Ver logs do Antivírus ClamAV (`clamav-logs`)**: Acompanha atualizações de banco de dados e atividade do antivírus em tempo real.

### 📂 Central de Logs Persistidos (`./logs/`) e Retenção de 60 Dias
- **27. Listar todos os arquivos de logs persistidos (`logs-list`)**: Exibe todos os arquivos de log gravados no disco nas subpastas (`alerts/`, `traefik/`, `waf/`, `caddy/`, `php/`, `cron/`).
- **28. Inspecionar tamanho e últimos logs gravados (`logs-tail`)**: Mostra o tamanho em disco, última alteração e linhas mais recentes dos arquivos de log.
- **29. LIMPAR e Zerar todos os arquivos de logs (`logs-clear`)**: Esvazia e zera com segurança os logs de todos os componentes da stack.

### 💻 Manutenção do Windows (Apenas `manager.bat`)
- **30. Listar máquinas virtuais do WSL (`wsl-list`)**: Exibe o status e as versões das distribuições Linux virtuais rodando por baixo do Windows.
- **31. Forçar desligamento do WSL (`wsl-shutdown`)**: Força o núcleo hipervisor do WSL2 a desligar e limpar o cache da memória RAM em caso de travamentos do Docker Desktop no Windows.

---

## 🔧 Dicas de Manutenção Avançada

### Política de Expurgo Automático de Logs
Todos os logs gerados em `./logs/` possuem expurgo automático diário gerenciado pelo contêiner sentinela (`resource_monitor`), eliminando automaticamente arquivos com mais de 60 dias (`LOG_RETENTION_DAYS=60` no `.env`).

### Instalar ou Atualizar Extensões do PHP
As extensões PHP do projeto são instaladas no `/php/Dockerfile`. Se você precisar de uma nova extensão, edite o `Dockerfile` e adicione o nome dela na lista do `install-php-extensions`.
Após salvar a edição, execute a opção **`5. Reconstruir as imagens (build)`** no seu gerenciador.

