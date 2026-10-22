FROM python:3.9-slim

WORKDIR /app

RUN pip install --no-cache-dir docker

COPY Master-Cron/master_scheduler.py /app/master_scheduler.py
COPY Jobs/tasks/tasks.json /app/tasks.json

CMD ["python", "-u", "master_scheduler.py"]
