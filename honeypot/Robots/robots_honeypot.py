#!/usr/bin/env python3
"""
Honeypot para ROBOS (scanners, brute-force, exploit kits, crawlers maliciosos).

Diferente do honeypot de IA (Moqesh), aqui o alvo sao bots "burros" que varrem
caminhos conhecidos (wp-login.php, xmlrpc.php, phpmyadmin, shells...). Eles nao
leem conteudo, entao a estrategia e:

  1. Servir iscas criveis (login WordPress falso, phpMyAdmin falso, etc.)
  2. Tarpit: responder devagar (drip byte a byte) para prender o bot
  3. Registrar tudo em JSON lines (/logs/robots.log)
  4. Adicionar o IP na blocklist compartilhada lida pelos WAFs (geo $bad_ip)

Somente stdlib - nenhuma dependencia externa. Nada recebido e executado.
"""
from __future__ import annotations

import fcntl
import ipaddress
import json
import os
import random
import re
import threading
import time
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

# ------------------------------------------------------------------------------
# Configuracao (variaveis de ambiente)
# ------------------------------------------------------------------------------
PORT = int(os.environ.get("ROBOTS_PORT", "8081"))
LOG_FILE = os.environ.get("ROBOTS_LOG_FILE", "/logs/robots.log")
BLOCKLIST_FILE = os.environ.get("BLOCKLIST_FILE", "/blocklist/honeypot_blocklist.txt")
# Quantas requisicoes a iscas antes de bloquear (1 = bloqueio no primeiro toque)
# URL de punicao para invasores insistentes (Capitao Nascimento: "Pede pra sair!")
TROLL_REDIRECT_URL = os.environ.get(
    "ROBOTS_TROLL_REDIRECT_URL",
    "https://www.yout-ube.com/watch?v=TwIsz1BO3Dc"
)
INSISTENT_THRESHOLD = int(os.environ.get("ROBOTS_INSISTENT_THRESHOLD", "4"))
BLOCK_THRESHOLD = int(os.environ.get("ROBOTS_BLOCK_THRESHOLD", "2"))
# Tarpit: atraso entre cada chunk enviado (segundos) e duracao maxima
TARPIT_CHUNK_DELAY = float(os.environ.get("ROBOTS_TARPIT_CHUNK_DELAY", "1.5"))
TARPIT_MAX_SECONDS = float(os.environ.get("ROBOTS_TARPIT_MAX_SECONDS", "60"))
MAX_TARPIT_CONNECTIONS = int(os.environ.get("ROBOTS_MAX_TARPIT_CONNECTIONS", "50"))
# IPs/redes que nunca sao bloqueadas (separadas por virgula)
WHITELIST = [
    ipaddress.ip_network(n.strip(), strict=False)
    for n in os.environ.get("HONEYPOT_WHITELIST", "127.0.0.1/32,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16").split(",")
    if n.strip()
]

_hits: dict[str, int] = defaultdict(int)
_lock = threading.Lock()
_tarpit_slots = threading.BoundedSemaphore(MAX_TARPIT_CONNECTIONS)

# ------------------------------------------------------------------------------
# Iscas
# ------------------------------------------------------------------------------
WP_LOGIN = """<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>Acessar &lsaquo; Site &#8212; WordPress</title>
<meta name="robots" content="noindex,nofollow"></head>
<body class="login"><div id="login"><h1><a href="https://br.wordpress.org/">Desenvolvido com WordPress</a></h1>
<form name="loginform" id="loginform" action="/wp-login.php" method="post">
<p><label for="user_login">Nome de usuario ou endereco de e-mail</label>
<input type="text" name="log" id="user_login" size="20"></p>
<p><label for="user_pass">Senha</label><input type="password" name="pwd" id="user_pass" size="20"></p>
<p class="submit"><input type="submit" name="wp-submit" id="wp-submit" value="Acessar">
<input type="hidden" name="redirect_to" value="/wp-admin/"><input type="hidden" name="testcookie" value="1"></p>
</form>%s</div></body></html>"""

PMA_LOGIN = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>phpMyAdmin</title></head>
<body><div class="container"><h1>Bem-vindo ao <bdo dir="ltr" lang="en">phpMyAdmin</bdo></h1>
<form method="post" action="index.php" name="login_form">
<fieldset><legend>Login</legend>
<div class="item"><label for="input_username">Usuario:</label><input type="text" name="pma_username" id="input_username"></div>
<div class="item"><label for="input_password">Senha:</label><input type="password" name="pma_password" id="input_password"></div>
<input type="hidden" name="server" value="1"></fieldset>
<fieldset class="tblFooters"><input value="Executar" type="submit" id="input_go"></fieldset>
</form>%s</div></body></html>"""

XMLRPC_FAULT = """<?xml version="1.0" encoding="UTF-8"?>
<methodResponse><fault><value><struct>
<member><name>faultCode</name><value><int>403</int></value></member>
<member><name>faultString</name><value><string>Incorrect username or password.</string></value></member>
</struct></value></fault></methodResponse>"""

# prefixo -> tipo de isca
TRAPS: list[tuple[str, str]] = [
    ("/wp-login.php", "wp_login"),
    ("/wp-admin", "wp_login"),
    ("/wp-json", "tarpit"),
    ("/wp-content", "tarpit"),
    ("/wp-config", "tarpit"),
    ("/xmlrpc.php", "xmlrpc"),
    ("/phpmyadmin", "pma"),
    ("/pma", "pma"),
    ("/myadmin", "pma"),
    ("/adminer", "pma"),
    ("/administrator/", "tarpit"),
    ("/server-status", "tarpit"),
    ("/dockerfile", "tarpit"),
    ("/configuration.php.bak", "tarpit"),
    ("/config.php.bak", "tarpit"),
    ("/home.aspx", "tarpit"),
    ("/Faturas.aspx", "tarpit"),
    ("/___proxy_subdomain", "tarpit"),
    ("/@fs/", "tarpit"),
    ("/vendor/phpunit", "tarpit"),
    ("/cgi-bin", "tarpit"),
    ("/boaform", "tarpit"),
    ("/HNAP1", "tarpit"),
    ("/actuator", "tarpit"),
    ("/solr", "tarpit"),
    ("/shell.php", "tarpit"),
    ("/wso.php", "tarpit"),
    ("/c99.php", "tarpit"),
    ("/r57.php", "tarpit"),
    ("/alfa.php", "tarpit"),
    ("/eval-stdin.php", "tarpit"),
    ("/robots-trap", "tarpit"),  # link invisivel inserido no HTML (ver README)
]

# Regex de verificacao ativa com base nos ataques sofridos reportados pelo usuario:
# SQL Injection, Shell/RCE Injection, Vazamento de Arquivos Sensiveis e Scanners Maliciosos
REGEX_ATTACKS: list[tuple[str, re.Pattern]] = [
    ("sql_injection", re.compile(
        r"(?i)(?:\bUNION\b.*\bSELECT\b)|(?:\bSELECT\b.*\bFROM\b)|(?:\bINSERT\b.*\bINTO\b)|"
        r"(?:\bUPDATE\b.*\bSET\b)|(?:\bDELETE\b.*\bFROM\b)|(?:\bDROP\b.*\bTABLE\b)|(?:\bTRUNCATE\b)|"
        r"(?:\bINFORMATION_SCHEMA\b)|(?:\bLOAD_FILE\b)|(?:\bOUTFILE\b)|(?:\bBENCHMARK\b)|"
        r"(?:\bSLEEP\s*\()|(?:\bWAITFOR\s+DELAY\b)|(?:\bDBMS_PIPE\.RECEIVE_MESSAGE\b)|(?:\bCONVERT\s*\()|"
        r"(?:\bCAST\s*\()|(?:NULL\s*=\s*NULL)|(?:1\s*=\s*1)|(?:0\s*=\s*0)|(?:OR\s+1=1)|(?:'--|\*\/--|\#)|"
        r"(?:\bexec\b|\bexecute\b|\bdeclare\b)"
    )),
    ("rce_shell_injection", re.compile(
        r"(?i)(?:cmd=)|(?:\bbash\s*-c\b)|(?:\bsh\s*-c\b)|(?:\$\()|(?:%24\()|(?:`.*?`)|(?:%60)|"
        r"(?:\|\|)|(?:&&)|(?:%7c)|(?:\bcurl\b)|(?:\bwget\b)|(?:gsocket\.io)"
    )),
    ("sensitive_files", re.compile(
        r"(?i)(?:(?:\.|%2e)(?:env|git|aws|azure|gcp|ssh|kube|docker|github|gitlab|vscode|idea|claude|anthropic|openai|cursor|hermes|config|terraform|DS_Store|svn|bash|zsh|flaskenv|mcp\.json))|"
        r"(?:wp-(?:admin|json|content|config|login))|(?:administrator/)|(?:server-status)|(?:dockerfile)|"
        r"(?:(?:configuration|config)\.php\.bak)|(?:\.(?:bak|old|save|swp|orig|sql)(?:\b|$))|"
        r"(?:___proxy_subdomain)|(?:@fs/)|(?:\?author=\d+)|(?:\?rest_route=)|(?:home\.aspx)|(?:Faturas\.aspx)|(?:pscan-.*\.txt)"
    )),
    ("malicious_bots_scanners", re.compile(
        r"(?i)(sqlmap|nmap|masscan|nikto|w3af|hydra|scan|scrapy|libwww-perl|crusader-worker|censys|acme-spider|zspider|morfeus|dirbuster|havij)"
    ))
]


TZ_BR = ZoneInfo(os.environ.get("TZ", "America/Sao_Paulo"))


def agora() -> str:
    """Data/hora de Brasilia (ISO 8601 com offset -03:00)."""
    return datetime.now(TZ_BR).isoformat(timespec="seconds")


def is_whitelisted(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True  # IP invalido: nunca escreve na blocklist
    return any(addr in net for net in WHITELIST)


def append_blocklist(ip: str, reason: str) -> bool:
    """Adiciona 'IP 1;' (formato geo do Nginx) na blocklist compartilhada."""
    if is_whitelisted(ip):
        return False
    line = f"{ip} 1;"
    os.makedirs(os.path.dirname(BLOCKLIST_FILE), exist_ok=True)
    with open(BLOCKLIST_FILE, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        if any(l.strip() == line for l in fh):
            return False
        fh.write(f"# robots {agora()} {reason}\n{line}\n")
    return True


def log_event(event: dict) -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with _lock, open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def classify(path: str, full_query: str = "", ua: str = "", body: str = "") -> tuple[str | None, str | None]:
    """Classifica a requisicao checando prefixos e assinaturas de ataque."""
    target_data = f"{path}?{full_query} {body}"
    for attack_name, rx in REGEX_ATTACKS:
        if attack_name == "malicious_bots_scanners" and rx.search(ua):
            return "bot_scanner", attack_name
        if rx.search(target_data):
            # Se for uma das iscas especificas (ex: wp-login, pma, xmlrpc), mantem o kind da isca
            low = path.lower()
            for prefix, trap_kind in TRAPS:
                if low.startswith(prefix.lower()):
                    return trap_kind, attack_name
            return "exploit_attack", attack_name

    low = path.lower()
    for prefix, kind in TRAPS:
        if low.startswith(prefix.lower()):
            return kind, None
    return None, None


class Handler(BaseHTTPRequestHandler):
    server_version = "Apache/2.4.58 (Ubuntu)"
    sys_version = ""

    def log_message(self, fmt, *args):  # silencia log padrao (usamos JSON)
        pass

    # IP real vindo do Traefik
    def client_ip(self) -> str:
        for h in ("X-Real-Ip", "X-Forwarded-For"):
            v = self.headers.get(h)
            if v:
                return v.split(",")[0].strip()
        return self.client_address[0]

    def read_body(self) -> str:
        try:
            n = min(int(self.headers.get("Content-Length", "0")), 16384)
        except ValueError:
            n = 0
        return self.rfile.read(n).decode("utf-8", "replace") if n > 0 else ""

    def handle_any(self):
        ip = self.client_ip()
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_body() if self.command == "POST" else ""
        ua = self.headers.get("User-Agent", "")

        kind, attack_detected = classify(path, parsed.query, ua, body)
        kind = kind or "tarpit"

        creds = None
        if body and kind in ("wp_login", "pma"):
            form = parse_qs(body)
            user = (form.get("log") or form.get("pma_username") or [""])[0]
            pwd = (form.get("pwd") or form.get("pma_password") or [""])[0]
            # Nunca guardamos a senha em claro: apenas tamanho
            creds = {"user": user[:128], "password_len": len(pwd)}

        with _lock:
            _hits[ip] += 1
            hits = _hits[ip]

        # Se detectou SQLi, RCE, scanner bot ou tocou mais que o threshold -> Bloqueia imediatamente!
        is_direct_exploit = bool(attack_detected in ("sql_injection", "rce_shell_injection", "malicious_bots_scanners"))
        blocked = (is_direct_exploit or hits >= BLOCK_THRESHOLD) and append_blocklist(
            ip, f"{kind} {attack_detected or ''} {path}"
        )

        log_event({
            "ts": agora(), "honeypot": "robots", "ip": ip, "method": self.command,
            "path": self.path[:2048], "trap": kind, "attack": attack_detected,
            "hits": hits, "blocked_now": blocked,
            "ua": ua[:512], "creds": creds,
            "body_len": len(body),
        })

        # Invasor insistente: redireciona direto pro Capitao Nascimento
        if hits >= INSISTENT_THRESHOLD:
            self.send_response(302)
            self.send_header("Location", TROLL_REDIRECT_URL)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("X-Troll-Reason", "Pede pra sair!")
            self.end_headers()
            return

        if kind == "wp_login":
            err = '<div id="login_error"><strong>Erro:</strong> a senha informada esta incorreta.</div>' if creds else ""
            return self.respond(200, WP_LOGIN % err, "text/html; charset=UTF-8", slow=bool(creds))
        if kind == "pma":
            err = '<div class="alert alert-danger">Nao e possivel efetuar login no servidor MySQL</div>' if creds else ""
            return self.respond(200, PMA_LOGIN % err, "text/html; charset=utf-8", slow=bool(creds))
        if kind == "xmlrpc":
            if self.command == "POST":
                return self.respond(200, XMLRPC_FAULT, "text/xml; charset=UTF-8", slow=True)
            return self.respond(405, "XML-RPC server accepts POST requests only.", "text/plain")
        return self.tarpit()

    def respond(self, code: int, text: str, ctype: str, slow: bool = False):
        if slow:  # atraso tipico de bcrypt/login lento -> reduz taxa de brute-force
            time.sleep(random.uniform(2.0, 4.0))
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Powered-By", "PHP/7.4.33")
        self.end_headers()
        self.wfile.write(data)

    def tarpit(self):
        """Envia HTML infinito-ish byte a byte para prender o bot."""
        if not _tarpit_slots.acquire(blocking=False):
            return self.respond(404, "<h1>Not Found</h1>", "text/html")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=UTF-8")
            self.send_header("X-Powered-By", "PHP/7.4.33")
            self.end_headers()
            start = time.time()
            self.wfile.write(b"<!DOCTYPE html><html><head><title>Index of /</title></head><body>\n")
            while time.time() - start < TARPIT_MAX_SECONDS:
                name = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=8))
                self.wfile.write(f'<a href="{name}/">{name}/</a>\n'.encode())
                self.wfile.flush()
                time.sleep(TARPIT_CHUNK_DELAY)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            _tarpit_slots.release()

    def do_GET(self):
        if self.path == "/__health":
            return self.respond(200, "ok", "text/plain")
        self.handle_any()

    do_POST = do_HEAD = do_PUT = do_OPTIONS = handle_any


if __name__ == "__main__":
    ThreadingHTTPServer.daemon_threads = True
    print(f"[robots-honeypot] ouvindo em :{PORT} | blocklist={BLOCKLIST_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
