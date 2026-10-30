FROM python:3.12-alpine
ENV TZ=America/Sao_Paulo LANG=pt_BR.UTF-8 LC_ALL=pt_BR.UTF-8
RUN apk add --no-cache tzdata
RUN adduser -D -u 10001 honeypot
WORKDIR /app
COPY robots_honeypot.py .
USER honeypot
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1:8081/__health || exit 1
CMD ["python", "-u", "robots_honeypot.py"]
