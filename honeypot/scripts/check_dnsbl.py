#!/usr/bin/env python3
"""
Validador de IPs contra servidores DNSBL em tempo real ou sob demanda.
Configurado com suporte para consultas reversas aos principais provedores DNSBL/RBL.
Totalmente compativel com padroes de data/hora Brasilia (America/Sao_Paulo).
"""
from __future__ import annotations

import os
import socket
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_BR = ZoneInfo("America/Sao_Paulo")

DNSBL_SERVERS = [
    # Spamhaus
    "zen.spamhaus.org",
    "sbl.spamhaus.org",
    "xbl.spamhaus.org",
    "pbl.spamhaus.org",
    # SpamCop & SORBS
    "bl.spamcop.net",
    "dnsbl.sorbs.net",
    "dul.dnsbl.sorbs.net",
    "socks.dnsbl.sorbs.net",
    "http.dnsbl.sorbs.net",
    "smtp.dnsbl.sorbs.net",
    "web.dnsbl.sorbs.net",
    "zombie.dnsbl.sorbs.net",
    # Barracuda & SpamRATS
    "b.barracudacentral.org",
    "all.spamrats.com",
    "spam.spamrats.com",
    "dyna.spamrats.com",
    "noptr.spamrats.com",
    # Outros
    "rbl.megarbl.net",
    "spam.dnsbl.anonmails.de",
    "dnsbl.dronebl.org",
    "truncate.gbudb.net",
    "dnsbl-1.uceprotect.net",
    "dnsbl-2.uceprotect.net",
    "dnsbl-3.uceprotect.net",
    "psbl.surriel.com",
    "blacklist.woody.ch",
    "dnsbl.spfbl.net",
    "ubl.unsubscore.com",
]


def check_dnsbl(ip: str) -> dict[str, bool]:
    """Consulta o IP nos servidores DNSBL configurados."""
    octets = ip.strip().split(".")
    if len(octets) != 4:
        return {}
    reversed_ip = ".".join(reversed(octets))
    results = {}

    for server in DNSBL_SERVERS:
        query = f"{reversed_ip}.{server}"
        try:
            # Se resolver para 127.0.0.X, esta listado
            answers = socket.gethostbyname(query)
            if answers.startswith("127."):
                results[server] = True
        except (socket.gaierror, socket.herror, TimeoutError):
            results[server] = False

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python check_dnsbl.py <IP>")
        sys.exit(1)

    test_ip = sys.argv[1]
    agora = datetime.now(TZ_BR).strftime("%d/%m/%Y %H:%M:%S")
    print(f"[{agora}] Verificando IP: {test_ip} em {len(DNSBL_SERVERS)} servidores DNSBL...")

    hits = check_dnsbl(test_ip)
    listed = [s for s, is_listed in hits.items() if is_listed]

    if listed:
        print(f"🚨 ALERTA: IP {test_ip} listado em {len(listed)} DNSBLs:")
        for s in listed:
            print(f"  - {s}")
    else:
        print(f"✅ IP {test_ip} limpo nas listas consultadas.")

