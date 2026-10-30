#!/bin/sh
# ==============================================================================
# Coletor de logs Docker -> ./logs/docker/<container>.log
# Segue (docker logs -f) o stdout/stderr de todos os containers do projeto
# compose e reanexa automaticamente quando um container e recriado.
# ==============================================================================
PROJECT="${LOG_PROJECT:-php83}"
OUT="${LOG_DIR:-/logs}"
MAX_BYTES="${LOG_MAX_BYTES:-52428800}"   # 50 MB -> rotaciona para .1
export TZ="${TZ:-America/Sao_Paulo}"
apk add --no-cache tzdata >/dev/null 2>&1 || true
mkdir -p "$OUT" /tmp/pids

echo "[log-collector] projeto=$PROJECT destino=$OUT"
while true; do
    for c in $(docker ps --filter "label=com.docker.compose.project=$PROJECT" --format '{{.Names}}'); do
        pidf="/tmp/pids/$c.pid"
        if [ ! -f "$pidf" ] || ! kill -0 "$(cat "$pidf")" 2>/dev/null; then
            since=$(date -u +%Y-%m-%dT%H:%M:%S)
            [ -f "$pidf" ] || since="10m"   # primeira vez: ultimos 10 minutos
            # Prefixa cada linha com data/hora de Brasilia (dd/mm/aaaa HH:MM:SS)
            ( docker logs -f --since "$since" "$c" 2>&1 | awk '{ print strftime("%d/%m/%Y %H:%M:%S"), $0; fflush() }' >> "$OUT/$c.log" ) &
            echo $! > "$pidf"
            echo "[log-collector] seguindo $c"
        fi
        f="$OUT/$c.log"
        if [ -f "$f" ] && [ "$(stat -c %s "$f")" -gt "$MAX_BYTES" ]; then
            cp "$f" "$f.1" && : > "$f"
        fi
    done
    sleep 15
done
