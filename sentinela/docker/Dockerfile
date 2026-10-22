FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends clamav clamav-daemon && rm -rf /var/lib/apt/lists/*
RUN pip install docker cryptography pyclamd

COPY monitor/monitor.py /app/monitor.py
COPY emails/*.html /app/

CMD ["python", "monitor.py"]
