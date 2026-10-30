#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CTIR Gov Security Alerts Checker
Monitora continuamente os alertas e avisos de segurança emitidos pelo Centro de Prevenção,
Tratamento e Resposta a Incidentes Cibernéticos de Governo (CTIR Gov) em:
https://www.gov.br/gsi/pt-br/assuntos/ctir/alertas

Quando um novo alerta for detectado:
- Salva o alerta no arquivo de estado para não repetir o envio (ctir_alerts_seen.json)
- Dispara notificação via Telegram, E-mail e SMS (SMS Legal)
- Suporta execução no instalador (install.ps1 / install.sh) e em background/cron
"""

import os
import re
import ssl
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime

# Importa os canais de envio do monitor
try:
    from monitor import (
        broadcast_alert,
        write_alert_log,
        SERVER_DOMAIN,
        ALERT_CHANNEL_EMAIL,
        ALERT_CHANNEL_TELEGRAM,
        ALERT_CHANNEL_SMS
    )
except ImportError:
    # Fallback se executado isoladamente
    SERVER_DOMAIN = os.environ.get('DOMAIN', 'docker.charlescorrea.com.br')
    ALERT_CHANNEL_EMAIL = True
    ALERT_CHANNEL_TELEGRAM = True
    ALERT_CHANNEL_SMS = True

    def write_alert_log(entry):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{entry.get('channel', 'CTIR')}] {entry.get('subject', '')} - {entry.get('details', '')}")

    def broadcast_alert(subject, body_plain, body_html, short_summary=""):
        print(f"[BROADCAST] {subject}\n{body_plain[:200]}...")

LOGS_DIR = os.environ.get('LOGS_DIR', '/logs')
STATE_DIR = os.path.join(LOGS_DIR, "sentinela")
STATE_FILE = os.path.join(STATE_DIR, "ctir_alerts_seen.json")
CTIR_BASE_URL = "https://www.gov.br"
CTIR_MAIN_URL = "https://www.gov.br/gsi/pt-br/assuntos/ctir/alertas"

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def load_seen_alerts():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and "seen_ids" in data:
                    return data
        except Exception as e:
            print(f"[CTIR] Aviso: Erro ao carregar arquivo de estado {STATE_FILE}: {e}")
    return {"updated_at": "", "seen_ids": {}, "total_count": 0}

def save_seen_alerts(data):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        data["updated_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data["total_count"] = len(data.get("seen_ids", {}))
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[CTIR ERRO] Falha ao salvar estado em {STATE_FILE}: {e}")

def fetch_url(url, timeout=20):
    ctx = get_ssl_context()
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Enterprise-CTIR-Monitor/1.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }
    )
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def extract_alert_details(url):
    """Extrai o título, descrição e primeiro parágrafo de um alerta específico do CTIR Gov"""
    try:
        html = fetch_url(url, timeout=15)
        # Título
        title_match = re.search(r'<h1[^>]*class=["\'][^"\']*documentFirstHeading[^"\']*["\'][^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else ""

        # Descrição
        desc_match = re.search(r'<div[^>]*class=["\'][^"\']*documentDescription[^"\']*["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
        desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else ""

        # Conteúdo
        content_match = re.search(r'<div[^>]*id=["\']parent-fieldname-text["\'][^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<[^>]+>', ' ', content_match.group(1)).strip() if content_match else ""
        content = re.sub(r'\s+', ' ', content)

        return {
            'title': title,
            'description': desc,
            'summary': content[:400] + ('...' if len(content) > 400 else '')
        }
    except Exception as e:
        print(f"[CTIR] Aviso: Não foi possível obter detalhes de {url}: {e}")
        return {'title': '', 'description': '', 'summary': ''}

def check_ctir_gov_alerts(mark_initial_as_seen=False):
    """
    Varre a página do CTIR Gov em busca de novos alertas.
    Se mark_initial_as_seen=True (primeira execução), apenas inicializa a lista de alertas
    já existentes na base para não disparar enxurrada de alertas antigos, mas notifica
    que o monitoramento do CTIR Gov foi ativado com sucesso.
    """
    state = load_seen_alerts()
    seen = state.get("seen_ids", {})
    is_first_run = (len(seen) == 0)

    current_year = datetime.now().year
    years_to_check = [str(current_year)]
    if current_year > 2026:
        years_to_check.append("2026")

    discovered_alerts = []

    for yr in years_to_check:
        yr_url = f"{CTIR_MAIN_URL}/{yr}"
        try:
            html = fetch_url(yr_url, timeout=15)
            # Extrai links de alertas: href="https://www.gov.br/gsi/pt-br/assuntos/ctir/alertas/<ano>/alerta-..."
            matches = re.findall(
                rf'<a\s+[^>]*href=["\'](https://www\.gov\.br/gsi/pt-br/assuntos/ctir/alertas/{yr}/[^"\']+)["\'][^>]*>(.*?)</a>',
                html,
                re.DOTALL | re.IGNORECASE
            )
            for link, raw_title in matches:
                clean_title = re.sub(r'<[^>]+>', '', raw_title).strip()
                # Extrai identificador único, ex: alerta-104-2026
                alert_id = link.rstrip('/').split('/')[-1]
                if alert_id and clean_title:
                    discovered_alerts.append({
                        'id': alert_id,
                        'url': link,
                        'title': clean_title,
                        'year': yr
                    })
        except Exception as e:
            print(f"[CTIR] Aviso ao consultar ano {yr} ({yr_url}): {e}")

    # Remove duplicados preservando ordem
    unique_alerts = []
    seen_in_batch = set()
    for item in discovered_alerts:
        if item['id'] not in seen_in_batch:
            seen_in_batch.add(item['id'])
            unique_alerts.append(item)

    print(f"[CTIR GOV] Varredura concluída: {len(unique_alerts)} alertas encontrados no portal.")

    # Se for primeira execução e o usuário optou por marcar como lidos (baseline)
    if is_first_run and mark_initial_as_seen:
        for item in unique_alerts:
            seen[item['id']] = {
                'title': item['title'],
                'url': item['url'],
                'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'notified': False
            }
        save_seen_alerts(state)
        print(f"[CTIR GOV] Baseline configurada: {len(seen)} alertas históricos catalogados. Novos alertas serão monitorados e disparados.")
        
        # Dispara aviso de ativação do monitoramento
        sub = "🛡️ Monitor CTIR Gov de Segurança Cibernética Ativado"
        body_p = (
            "MONITORAMENTO CTIR GOV ATIVADO\n\n"
            f"Servidor: {SERVER_DOMAIN}\n"
            f"Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (Horário de Brasília)\n"
            f"Fonte Oficial: {CTIR_MAIN_URL}\n"
            f"Alertas históricos catalogados: {len(seen)}\n\n"
            "O cluster monitorará automaticamente novos alertas emitidos pelo Gabinete de Segurança Institucional (GSI/CTIR Gov) "
            "e disparará avisos imediatos via Telegram, E-mail e SMS."
        )
        body_h = (
            f"<h3>🛡️ Monitoramento de Alertas CTIR Gov Ativado</h3>"
            f"<p><b>Servidor:</b> {SERVER_DOMAIN}<br>"
            f"<b>Data/Hora:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (Brasília)<br>"
            f"<b>Fonte:</b> <a href='{CTIR_MAIN_URL}'>{CTIR_MAIN_URL}</a><br>"
            f"<b>Alertas históricos catalogados:</b> {len(seen)}</p>"
            f"<p>A partir de agora, qualquer novo comunicado de segurança nacional ou vulnerabilidade crítica emitido pelo CTIR Gov "
            f"será transmitido instantaneamente por todos os canais configurados.</p>"
        )
        broadcast_alert(sub, body_p, body_h, short_summary=f"Monitor CTIR Gov ativo no servidor {SERVER_DOMAIN}.")
        return

    # Processa novos alertas não vistos
    new_alerts = [a for a in unique_alerts if a['id'] not in seen]

    if not new_alerts:
        print("[CTIR GOV] Nenhum alerta novo emitido desde a última checagem.")
        return

    print(f"[CTIR GOV] 🚨 {len(new_alerts)} NOVO(S) ALERTA(S) DETECTADO(S)!")

    # Notifica do mais antigo para o mais recente para manter cronologia
    for item in reversed(new_alerts):
        details = extract_alert_details(item['url'])
        full_title = details['title'] if details['title'] else item['title']
        desc = details['description']
        summary = details['summary']

        subject = f"🚨 ALERTA DE SEGURANÇA CTIR GOV: {item['id'].upper()}"
        
        body_plain = (
            f"🚨 NOVO ALERTA OFICIAL CTIR GOV - CIBERSEGURANÇA\n\n"
            f"Identificador: {item['id'].upper()}\n"
            f"Título: {full_title}\n"
            f"Descrição: {desc}\n"
            f"Data/Hora da Detecção: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (Brasília)\n"
            f"Link Oficial: {item['url']}\n\n"
            f"Resumo da Ameaça:\n{summary}\n\n"
            f"Recomendação:\n"
            f"Acesse o link oficial do CTIR Gov para verificar se seus sistemas, bibliotecas e kernels "
            f"são afetados e aplique as correções e mitigações sugeridas imediatamente.\n\n"
            f"Servidor: {SERVER_DOMAIN}\n"
        )

        body_html = (
            f"<h2 style='color: #c0392b;'>🚨 Novo Alerta de Segurança Cibernética - CTIR Gov</h2>"
            f"<p><b>Identificador:</b> {item['id'].upper()}<br>"
            f"<b>Título:</b> {full_title}<br>"
            f"<b>Data/Hora da Notificação:</b> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} (Brasília)<br>"
            f"<b>Link Oficial:</b> <a href='{item['url']}'>{item['url']}</a></p>"
            f"<blockquote style='border-left: 4px solid #e74c3c; padding-left: 10px; color: #555;'>"
            f"<b>{desc}</b><br><br>{summary}"
            f"</blockquote>"
            f"<p><b>Ação Recomendada:</b> Consulte o comunicado completo no portal governamental e valide se há regras de WAF, patches de kernel ou atualizações de pacotes requeridas.</p>"
            f"<hr><p style='font-size: 11px; color: #888;'>Cluster de Proteção Sentinela - {SERVER_DOMAIN}</p>"
        )

        short_sms = f"ALERTA CTIR GOV {item['id'].upper()}: {desc[:60]}... Verifique: {item['url']}"

        print(f"[CTIR GOV] Disparando alerta {item['id']}...")
        broadcast_alert(subject, body_plain, body_html, short_summary=short_sms)

        # Salva imediatamente no estado para não reenviar em caso de interrupção
        seen[item['id']] = {
            'title': full_title,
            'url': item['url'],
            'description': desc,
            'first_seen': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'notified': True
        }
        save_seen_alerts(state)
        write_alert_log({
            'channel': 'ctir_gov',
            'status': 'DISPATCHED',
            'subject': subject,
            'details': f"Alerta {item['id']} despachado via canais configurados."
        })

if __name__ == '__main__':
    import sys
    # Se passado --init ou --baseline, apenas cataloga os existentes
    mark_baseline = ('--init' in sys.argv or '--baseline' in sys.argv)
    check_ctir_gov_alerts(mark_initial_as_seen=mark_baseline)
