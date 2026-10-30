#!/usr/bin/env python3
"""
Ponte Moqesh -> WAF.

O Moqesh bloqueia o agente de IA apenas dentro do proprio honeypot (403) e
dispara um webhook `attacker_blocked`. Esta ponte recebe esse webhook, valida a
assinatura HMAC (X-Moqesh-Signature: sha256=<hex>) e grava o IP na blocklist
compartilhada, que os WAFs carregam via `geo $bad_ip` -> bloqueio no site todo.

Somente stdlib. Escuta apenas na rede interna do Docker.
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import ipaddress
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("BRIDGE_PORT", "8090"))
SECRET = os.environ.get("MOQESH_WEBHOOK_SECRET", "")
BLOCKLIST_FILE = os.environ.get("BLOCKLIST_FILE", "/blocklist/honeypot_blocklist.txt")
LOG_FILE = os.environ.get("BRIDGE_LOG_FILE", "/logs/ia-bridge.log")
WHITELIST = [
    ipaddress.ip_network(n.strip(), strict=False)
    for n in os.environ.get("HONEYPOT_WHITELIST", "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16").split(",")
    if n.strip()
]


TZ_BR = ZoneInfo(os.environ.get("TZ", "America/Sao_Paulo"))


def agora() -> str:
    """Data/hora de Brasilia (ISO 8601 com offset -03:00)."""
    return datetime.now(TZ_BR).isoformat(timespec="seconds")


def valid_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return not any(addr in net for net in WHITELIST)


def append_blocklist(ip: str, reason: str) -> bool:
    line = f"{ip} 1;"
    os.makedirs(os.path.dirname(BLOCKLIST_FILE), exist_ok=True)
    with open(BLOCKLIST_FILE, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        if any(l.strip() == line for l in fh):
            return False
        safe_reason = reason.replace("\n", " ")[:200]
        fh.write(f"# ia {agora()} {safe_reason}\n{line}\n")
    return True


def log_event(event: dict) -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def reply(self, code: int, msg: str):
        data = msg.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply(200 if self.path == "/health" else 404, "ok" if self.path == "/health" else "not found")

    def do_POST(self):
        if self.path != "/hook/moqesh":
            return self.reply(404, "not found")
        try:
            n = min(int(self.headers.get("Content-Length", "0")), 65536)
        except ValueError:
            return self.reply(400, "bad length")
        body = self.rfile.read(n)

        if not SECRET:
            return self.reply(503, "MOQESH_WEBHOOK_SECRET nao configurado")
        expected = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, self.headers.get("X-Moqesh-Signature", "")):
            return self.reply(401, "assinatura invalida")

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return self.reply(400, "json invalido")

        ip = str(payload.get("ip", "")).strip()
        added = False
        if payload.get("event") == "attacker_blocked" and valid_public_ip(ip):
            added = append_blocklist(ip, f"{payload.get('source')} {payload.get('reason')}")
        log_event({"ts": agora(), "honeypot": "ia", "ip": ip, "added": added, "payload": payload})
        self.reply(200, "ok")


if __name__ == "__main__":
    print(f"[ia-bridge] ouvindo em :{PORT} | blocklist={BLOCKLIST_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
