#!/bin/bash
# Verificação de requisitos de hardware e sistema para Linux/Mac

min_host_ram_kb=$((12 * 1024 * 1024))
min_docker_ram_kb=$((4 * 1024 * 1024))
min_free_disk_kb=$((15 * 1024 * 1024))

echo "======================================================="
echo "   Verificando Requisitos de Sistema (Docker 8.5)      "
echo "======================================================="

has_errors=0

# 1. Verifica se Docker está rodando
if ! docker info >/dev/null 2>&1; then
    echo " [ERRO] O daemon do Docker não está rodando ou o usuário atual não tem permissão!"
    echo "        Inicie o Docker ou adicione seu usuário ao grupo docker (sudo usermod -aG docker \$USER)."
    exit 1
fi

docker_mem_bytes=$(docker info --format '{{.MemTotal}}' 2>/dev/null)
docker_cpus=$(docker info --format '{{.NCPU}}' 2>/dev/null)
docker_mem_gb=$(awk "BEGIN {printf \"%.1f\", $docker_mem_bytes / 1024 / 1024 / 1024}")

# 2. Host RAM
if [ -f /proc/meminfo ]; then
    host_ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    host_ram_gb=$(awk "BEGIN {printf \"%.1f\", $host_ram_kb / 1024 / 1024}")
    if [ "$host_ram_kb" -lt "$min_host_ram_kb" ]; then
        echo " [ERRO] Memória RAM do Host insuficiente: ${host_ram_gb} GB detectados (Mínimo: 12 GB | Recomendado: 16 GB)."
        has_errors=1
    else
        echo " [OK] Memória RAM do Host: ${host_ram_gb} GB (Mínimo: 12 GB | Recomendado: 16 GB)"
    fi
fi

# 3. Docker RAM
docker_mem_kb=$(awk "BEGIN {printf \"%.0f\", $docker_mem_bytes / 1024}")
if [ "$docker_mem_kb" -lt "$min_docker_ram_kb" ]; then
    echo " [ERRO] Memória alocada no Docker insuficiente: apenas ${docker_mem_gb} GB."
    echo "        O ClamAV consome até 2.5 GB para carregar assinaturas em memória."
    echo "        Recomendado alocar pelo menos 4 GB a 6 GB para o Docker."
    has_errors=1
else
    echo " [OK] Memória alocada para o Docker: ${docker_mem_gb} GB (Mínimo: 4 GB)"
fi

# 4. CPUs
if [ "$docker_cpus" -ge 2 ]; then
    echo " [OK] Núcleos de CPU disponíveis no Docker: $docker_cpus núcleos"
else
    echo " [AVISO] Apenas $docker_cpus núcleo disponível. Recomendado: 2 ou mais núcleos."
fi

# 5. Disco Livre
free_disk_kb=$(df -k . | awk 'NR==2 {print $4}')
free_disk_gb=$(awk "BEGIN {printf \"%.1f\", $free_disk_kb / 1024 / 1024}")
if [ "$free_disk_kb" -lt "$min_free_disk_kb" ]; then
    echo " [ERRO] Espaço em disco insuficiente: apenas ${free_disk_gb} GB livres (Mínimo: 15 GB)."
    has_errors=1
else
    echo " [OK] Espaço Livre em Disco: ${free_disk_gb} GB (Mínimo: 15 GB)"
fi

echo "-------------------------------------------------------"

if [ "$has_errors" -eq 1 ]; then
    echo " [BLOQUEADO] O sistema não atende aos requisitos mínimos obrigatórios."
    echo "             Ajuste os recursos antes de iniciar a infraestrutura."
    exit 1
else
    echo " [SUCESSO] Todos os requisitos de hardware e ambiente foram atendidos!"
    exit 0
fi
