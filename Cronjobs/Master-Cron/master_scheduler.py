import os
import time
import json
import docker
from datetime import datetime

CONFIG_PATH = os.environ.get('CRON_TASKS_CONFIG', '/app/tasks.json')

def load_tasks():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f).get('tasks', [])
        except Exception as e:
            print(f"[MASTER-CRON ERROR] Erro ao carregar config de tarefas: {e}")
    return []

def run_master_scheduler():
    print("=" * 60)
    print(" [MASTER-CRON] Orquestrador Enterprise de Tarefas Iniciado")
    print("=" * 60)
    
    try:
        client = docker.from_env()
    except Exception as e:
        print(f"[MASTER-CRON ERROR] Não foi possível conectar ao Docker Socket: {e}")
        return

    last_runs = {}

    while True:
        tasks = load_tasks()
        now = time.time()

        for task in tasks:
            if not task.get('enabled', True):
                continue

            task_id = task['id']
            # Intervalo em segundos
            interval = task.get('schedule_hours', 0) * 3600 + task.get('schedule_minutes', 0) * 60
            if interval <= 0:
                interval = 3600

            last_run = last_runs.get(task_id, 0)
            if now - last_run >= interval:
                print(f"[MASTER-CRON] Disparando tarefa: {task.get('name', task_id)}...")
                target_script = task.get('target_script')
                pattern = task.get('target_container_pattern', '')

                if pattern and target_script:
                    try:
                        for c in client.containers.list():
                            if pattern in c.name.lower():
                                print(f"  -> Executando '{target_script}' no contêiner {c.name}")
                                res = c.exec_run(f"sh {target_script}")
                                print(f"  -> Resultado ({c.name}): exit_code={res.exit_code}")
                    except Exception as err:
                        print(f"[MASTER-CRON ERROR] Falha na execução da tarefa {task_id}: {err}")

                last_runs[task_id] = now

        time.sleep(30)

if __name__ == '__main__':
    run_master_scheduler()
