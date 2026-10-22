import os
import time
import json
import base64
import shutil
import smtplib
import subprocess
from datetime import datetime
import docker
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import warnings
warnings.filterwarnings('ignore', category=UserWarning)

import urllib.request
import urllib.parse

# Importação de criptografia SSL nativa
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
SMTP_FROM = os.environ.get('SMTP_FROM')
SMTP_TO = os.environ.get('SMTP_TO')
SERVER_DOMAIN = os.environ.get('DOMAIN', 'docker.charlescorrea.com.br')

# Seleção de Canais de Alerta Ativos (true/false)
def parse_bool_env(var_name, default=True):
    val = os.environ.get(var_name, '').strip().lower()
    if val in ('true', '1', 'yes', 'sim', 'on'):
        return True
    if val in ('false', '0', 'no', 'nao', 'não', 'off'):
        return False
    return default

ALERT_CHANNEL_EMAIL = parse_bool_env('ALERT_CHANNEL_EMAIL', True)
ALERT_CHANNEL_TELEGRAM = parse_bool_env('ALERT_CHANNEL_TELEGRAM', True)
ALERT_CHANNEL_SMS = parse_bool_env('ALERT_CHANNEL_SMS', True)

# Configurações do Provedor SMS Legal (https://v1.smsgateway.com.br/api/)
SMS_LEGAL_TOKEN = os.environ.get('SMS_LEGAL_TOKEN', '').strip()
SMS_LEGAL_TO = os.environ.get('SMS_LEGAL_TO', '').strip()

# Configurações do Telegram Bot API (https://core.telegram.org/bots/api)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
TELEGRAM_CHAT_IDS = os.environ.get('TELEGRAM_CHAT_IDS', os.environ.get('TELEGRAM_CHAT_ID', '')).strip()

# Limiares de alerta configurados em 70%
CPU_THRESHOLD = float(os.environ.get('CPU_THRESHOLD', 70.0))
MEM_THRESHOLD = float(os.environ.get('MEM_THRESHOLD', 70.0))
DISK_THRESHOLD = float(os.environ.get('DISK_THRESHOLD', 70.0))

CLAMAV_HOST = os.environ.get('CLAMAV_HOST', 'clamav')
CLAMAV_PORT = int(os.environ.get('CLAMAV_PORT', 3310))
SCAN_DIR = os.environ.get('SCAN_DIR', '/scandata')
QUARANTINE_DIR = os.environ.get('QUARANTINE_DIR', '/quarantine')
LOGS_DIR = os.environ.get('LOGS_DIR', '/logs')
LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', 60))

CERTS_DIR = '/certs'
LETSENCRYPT_DIR = '/letsencrypt'

client = docker.from_env()

def write_alert_log(entry):
    """
    Grava logs de alerta em arquivos diários dentro de /logs/ (ex: alerts_2026-10-19.log)
    com retenção configurada para 60 dias.
    """
    try:
        sentinela_logs_dir = os.path.join(LOGS_DIR, "sentinela")
        os.makedirs(sentinela_logs_dir, exist_ok=True)
        today_str = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(sentinela_logs_dir, f"alerts_{today_str}.log")
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        line = f"[{timestamp}] [{entry.get('channel', 'GENERAL').upper()}] [{entry.get('status', 'INFO')}] {entry.get('subject', '')} - {entry.get('details', '')}\n"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(line)
    except Exception as e:
        print(f"[LOG ERROR] Falha ao gravar log em {LOGS_DIR}: {str(e)}")

def purge_old_alert_logs():
    """
    Varre recursivamente todo o diretório /logs/ (incluindo subpastas de php, caddy, traefik, waf, cron, alerts)
    e apaga qualquer arquivo de log com mais de 60 dias (LOG_RETENTION_DAYS).
    """
    try:
        if not os.path.exists(LOGS_DIR):
            return
        now = time.time()
        max_age_seconds = LOG_RETENTION_DAYS * 86400
        count_purged = 0

        for root, dirs, files in os.walk(LOGS_DIR):
            for fname in files:
                if fname.endswith(".log") or fname.endswith(".txt") or fname.endswith(".gz"):
                    fpath = os.path.join(root, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        if (now - mtime) > max_age_seconds:
                            os.remove(fpath)
                            count_purged += 1
                            print(f"[LOG PURGE] Log removido (> {LOG_RETENTION_DAYS} dias): {os.path.relpath(fpath, LOGS_DIR)}")
                    except Exception as file_err:
                        print(f"[LOG PURGE ERROR] Falha ao avaliar {fpath}: {file_err}")

        if count_purged > 0:
            print(f"[LOG PURGE] Total de {count_purged} arquivos de log expurgados.")
    except Exception as e:
        print(f"[LOG PURGE ERROR] Falha no expurgo recursivo de logs: {str(e)}")



def send_email(subject, body_plain, body_html):
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        write_alert_log({'channel': 'email', 'status': 'SKIPPED', 'subject': subject, 'details': 'Credenciais SMTP incompletas'})
        return
    msg = MIMEMultipart('alternative')
    msg['From'] = SMTP_FROM
    msg['To'] = SMTP_TO
    msg['Subject'] = subject

    part1 = MIMEText(body_plain, 'plain', 'utf-8')
    part2 = MIMEText(body_html, 'html', 'utf-8')
    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_FROM, SMTP_TO, msg.as_string())
        server.quit()
        print(f"[EMAIL] Alerta enviado com sucesso: {subject}")
        write_alert_log({'channel': 'email', 'status': 'SUCCESS', 'subject': subject, 'details': f'Enviado para {SMTP_TO}'})
    except Exception as e:
        print(f"[EMAIL ERROR] Falha ao enviar email: {str(e)}")
        write_alert_log({'channel': 'email', 'status': 'ERROR', 'subject': subject, 'details': str(e)})

def sanitize_sms_text(text):
    """Remove acentos e caracteres que costumam ser bloqueados pelas operadoras de telefonia"""
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'Ç': 'C',
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E',
        'Í': 'I', 'Ì': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O',
        'Ú': 'U', 'Ù': 'U',
        '[': '(', ']': ')', '{': '(', '}': ')',
        '/': '-', '\\': '-',
        '⚠️': '', '🚨': '', '🔒': '', 'ℹ️': '', '⚡': ''
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    return text

def send_sms_legal(message_text):
    """
    Dispara SMS através da API SMS Legal (https://v1.smsgateway.com.br/api/send-sms-texto.php)
    Parâmetros: token, to, msg
    """
    if not SMS_LEGAL_TOKEN or not SMS_LEGAL_TO:
        write_alert_log({'channel': 'sms', 'status': 'SKIPPED', 'subject': 'Disparo SMS', 'details': 'Token ou Destinatario SMS ausente'})
        return

    # Limita o texto do SMS em ate 140 caracteres (garante compatibilidade total e 1 credito por envio)
    clean_msg = sanitize_sms_text(message_text).replace('\n', ' ')
    if len(clean_msg) > 140:
        clean_msg = clean_msg[:137] + '...'

    # Suporta múltiplos números separados por vírgula
    destinatarios = [num.strip() for num in SMS_LEGAL_TO.split(',') if num.strip()]

    for dest in destinatarios:
        params = urllib.parse.urlencode({
            'token': SMS_LEGAL_TOKEN,
            'to': dest,
            'msg': clean_msg
        })
        url = f"https://v1.smsgateway.com.br/api/send-sms-texto.php?{params}"

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Enterprise-Monitor/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8').strip()
                print(f"[SMS LEGAL] Mensagem enviada para {dest}. Resposta: {res_body}")
                write_alert_log({'channel': 'sms', 'status': 'SUCCESS', 'subject': clean_msg, 'details': f'Destino: {dest} | Resposta: {res_body}'})
        except Exception as e:
            print(f"[SMS LEGAL ERROR] Falha ao enviar SMS para {dest}: {str(e)}")
            write_alert_log({'channel': 'sms', 'status': 'ERROR', 'subject': clean_msg, 'details': f'Destino: {dest} | Erro: {str(e)}'})


def send_telegram(message_text):
    """
    Dispara notificação via Telegram Bot API (https://core.telegram.org/bots/api#sendmessage)
    Suporta múltiplos CHAT_IDS separados por vírgula e formatação HTML nativa.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        write_alert_log({'channel': 'telegram', 'status': 'SKIPPED', 'subject': 'Disparo Telegram', 'details': 'Token ou Chat ID do Telegram ausente'})
        return

    chat_ids = [cid.strip() for cid in TELEGRAM_CHAT_IDS.split(',') if cid.strip()]
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for chat_id in chat_ids:
        payload = json.dumps({
            'chat_id': chat_id,
            'text': message_text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }).encode('utf-8')

        try:
            req = urllib.request.Request(
                telegram_url,
                data=payload,
                headers={'Content-Type': 'application/json', 'User-Agent': 'Enterprise-Monitor/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8').strip()
                print(f"[TELEGRAM] Alerta enviado para o chat {chat_id}.")
                write_alert_log({'channel': 'telegram', 'status': 'SUCCESS', 'subject': 'Notificacao Bot', 'details': f'Chat ID: {chat_id}'})
        except Exception as e:
            print(f"[TELEGRAM ERROR] Falha ao enviar mensagem para chat {chat_id}: {str(e)}")
            write_alert_log({'channel': 'telegram', 'status': 'ERROR', 'subject': 'Notificacao Bot', 'details': f'Chat ID: {chat_id} | Erro: {str(e)}'})

def broadcast_alert(subject, body_plain, body_html, short_summary=""):
    """
    Transmite o alerta em paralelo para os canais ativados via variáveis de ambiente:
    1. E-mail (ALERT_CHANNEL_EMAIL)
    2. Telegram Bot (ALERT_CHANNEL_TELEGRAM)
    3. SMS Legal (ALERT_CHANNEL_SMS)
    """
    # Registra no log de auditoria a emissão do alerta pelo sentinela
    write_alert_log({'channel': 'monitor', 'status': 'BROADCAST', 'subject': subject, 'details': short_summary or body_plain[:100]})

    # 1. Envio por E-mail
    if ALERT_CHANNEL_EMAIL:
        send_email(subject, body_plain, body_html)
    else:
        print("[ALERTA] Canal de E-MAIL desativado por configuração (ALERT_CHANNEL_EMAIL=false).")
        write_alert_log({'channel': 'email', 'status': 'DISABLED', 'subject': subject, 'details': 'ALERT_CHANNEL_EMAIL=false'})

    # 2. Envio por Telegram (Formatação HTML)
    if ALERT_CHANNEL_TELEGRAM:
        telegram_text = f"<b>{subject}</b>\n\n<pre>{body_plain}</pre>"
        send_telegram(telegram_text)
    else:
        print("[ALERTA] Canal de TELEGRAM desativado por configuração (ALERT_CHANNEL_TELEGRAM=false).")
        write_alert_log({'channel': 'telegram', 'status': 'DISABLED', 'subject': subject, 'details': 'ALERT_CHANNEL_TELEGRAM=false'})

    # 3. Envio por SMS Legal
    if ALERT_CHANNEL_SMS:
        sms_text = short_summary if short_summary else f"{subject}: {body_plain[:100]}"
        send_sms_legal(sms_text)
    else:
        print("[ALERTA] Canal de SMS desativado por configuração (ALERT_CHANNEL_SMS=false).")
        write_alert_log({'channel': 'sms', 'status': 'DISABLED', 'subject': subject, 'details': 'ALERT_CHANNEL_SMS=false'})


def send_resource_alert(alert_type, target_name, cpu_percent, mem_percent, mem_usage_str, disk_percent, disk_usage_str, details_header, details_info, recommendation_text):
    alert_titles = {
        'cpu': 'Alerta de Alta Utilização de CPU',
        'memory': 'Alerta de Alto Consumo de Memória RAM',
        'disk': 'Alerta de Esgotamento de Espaço em Disco (HD)'
    }
    title = alert_titles.get(alert_type, 'Alerta de Utilização de Recursos')

    body_plain = f"{title.upper()}\n\n"
    body_plain += f"Domínio / URL: https://{SERVER_DOMAIN}\n"
    body_plain += f"Alvo / Recurso: {target_name}\n"
    body_plain += f"Uso de CPU: {cpu_percent:.1f}%\n"
    body_plain += f"Uso de Memória RAM: {mem_percent:.1f}% ({mem_usage_str})\n"
    body_plain += f"Uso de Disco (HD): {disk_percent:.1f}% ({disk_usage_str})\n\n"
    body_plain += f"{details_header}:\n{details_info}\n\n"
    body_plain += f"Recomendação:\n{recommendation_text}\n"

    try:
        with open('email_template.html', 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('{{ ALERT_TITLE }}', title)
        html = html.replace('{{ DOMAIN }}', SERVER_DOMAIN)
        html = html.replace('{{ TARGET_NAME }}', target_name)
        html = html.replace('{{ CPU_PERCENT }}', f"{cpu_percent:.1f}")
        html = html.replace('{{ MEM_PERCENT }}', f"{mem_percent:.1f}")
        html = html.replace('{{ MEM_USAGE }}', mem_usage_str)
        html = html.replace('{{ DISK_PERCENT }}', f"{disk_percent:.1f}")
        html = html.replace('{{ DISK_USAGE }}', disk_usage_str)
        html = html.replace('{{ DETAILS_HEADER }}', details_header)
        html = html.replace('{{ DETAILS_INFO }}', details_info)
        html = html.replace('{{ RECOMMENDATION_TEXT }}', recommendation_text)
    except Exception as e:
        html = f"<html><body><pre>{body_plain}</pre></body></html>"

    subject = f"[{SERVER_DOMAIN}] ⚠️ {title} ({target_name})"
    short_sms = f"Alerta ({SERVER_DOMAIN}): {title} em {target_name}. CPU {cpu_percent:.0f}%, RAM {mem_percent:.0f}%, HD {disk_percent:.0f}%."
    broadcast_alert(subject, body_plain, html, short_summary=short_sms)

def send_antivirus_alert(infected_file, virus_name, scan_details, dest_path):
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    year_str = str(datetime.now().year)

    body_plain = f"ALERTA DE SEGURANÇA (ClamAV)\n\n"
    body_plain += f"Domínio / URL Afetado: https://{SERVER_DOMAIN}\n"
    body_plain += f"Ameaça detectada: {virus_name}\n"
    body_plain += f"Arquivo infectado: {infected_file}\n"
    body_plain += f"Data/Hora: {now_str}\n"
    body_plain += f"Isolado para: {dest_path}\n\n"
    body_plain += f"Detalhes do scanner:\n{scan_details}\n"

    try:
        with open('antivirus_template.html', 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('{{ DOMAIN }}', SERVER_DOMAIN)
        html = html.replace('{{ INFECTED_FILE }}', infected_file)
        html = html.replace('{{ VIRUS_NAME }}', virus_name)
        html = html.replace('{{ DETECTED_AT }}', now_str)
        html = html.replace('{{ QUARANTINE_PATH }}', dest_path)
        html = html.replace('{{ SCAN_DETAILS }}', scan_details)
        html = html.replace('{{ YEAR }}', year_str)
    except Exception as e:
        html = f"<html><body><pre>{body_plain}</pre></body></html>"

    subject = f"[{SERVER_DOMAIN}] 🚨 ALERTA CRÍTICO: Malware neutralizado ({virus_name})"
    short_sms = f"Alerta Seguranca ({SERVER_DOMAIN}): Ameaca {virus_name} detectada e isolada em quarentena."
    broadcast_alert(subject, body_plain, html, short_summary=short_sms)

def send_ssl_notification(event_type, days_remaining, expiry_date_str, issuer_str, serial_str):
    """
    event_type: 'renewed', 'warning_30', 'warning_10', 'expired'
    """
    if event_type == 'renewed':
        title = "Certificado SSL/TLS Renovado com Sucesso"
        subtitle = "A renovação automática do certificado HTTPS foi concluída"
        status_label = "RENOVADO &bull; ATIVO"
        tip_title = "Operação Normal"
        tip_text = "O Traefik atualizou a cadeia de certificados e o tráfego HTTPS segue protegido e criptografado normalmente."
        message = f"O certificado de segurança SSL para o domínio <strong>https://{SERVER_DOMAIN}</strong> foi renovado com sucesso."
        subject = f"[{SERVER_DOMAIN}] 🔒 SUCESSO: Certificado SSL Renovado com Sucesso"
    elif event_type == 'warning_10':
        title = "Atenção Crítica: Certificado SSL Expira em 10 Dias"
        subtitle = "Prazo de segurança crítico atingido sem renovação detectada"
        status_label = "EXPIRA EM BREVE (URGENTE)"
        tip_title = "Ação Necessária"
        tip_text = "Verifique os logs do Traefik/ACME via comando 'docker compose logs load_balancer' para auditar se o desafio HTTP-01/TLS-ALPN está encontrando falhas de DNS."
        message = f"Restam apenas <strong>{days_remaining} dias</strong> para o vencimento do certificado HTTPS em <strong>https://{SERVER_DOMAIN}</strong>."
        subject = f"[{SERVER_DOMAIN}] ⚠️ URGENTE: Certificado SSL expira em {days_remaining} dias"
    else:  # warning_30
        title = "Aviso Prévio: Certificado SSL Expira em 30 Dias"
        subtitle = "Janela padrão de renovação automática do Let's Encrypt iniciada"
        status_label = "JANELA DE RENOVAÇÃO"
        tip_title = "Procedimento Automático"
        tip_text = "O Let's Encrypt inicia as tentativas automáticas de renovação 30 dias antes do vencimento. Acompanhe se a renovação ocorrerá normalmente nos próximos dias."
        message = f"O certificado SSL de <strong>https://{SERVER_DOMAIN}</strong> entrará em expiração em <strong>{days_remaining} dias</strong>."
        subject = f"[{SERVER_DOMAIN}] ℹ️ AVISO: Certificado SSL expira em {days_remaining} dias"

    body_plain = f"{title.upper()}\n\n"
    body_plain += f"Domínio: https://{SERVER_DOMAIN}\n"
    body_plain += f"Dias Restantes: {days_remaining} dias\n"
    body_plain += f"Data de Expiração: {expiry_date_str}\n"
    body_plain += f"Emissor: {issuer_str}\n"
    body_plain += f"Serial: {serial_str}\n\n"
    body_plain += f"{tip_title}: {tip_text}\n"

    try:
        with open('ssl_template.html', 'r', encoding='utf-8') as f:
            html = f.read()
        html = html.replace('{{ SSL_TITLE }}', title)
        html = html.replace('{{ SSL_SUBTITLE }}', subtitle)
        html = html.replace('{{ DOMAIN }}', SERVER_DOMAIN)
        html = html.replace('{{ SSL_MESSAGE }}', message)
        html = html.replace('{{ STATUS_LABEL }}', status_label)
        html = html.replace('{{ DAYS_REMAINING }}', str(days_remaining))
        html = html.replace('{{ EXPIRY_DATE }}', expiry_date_str)
        html = html.replace('{{ ISSUER }}', issuer_str)
        html = html.replace('{{ SERIAL_NUMBER }}', serial_str)
        html = html.replace('{{ TIP_TITLE }}', tip_title)
        html = html.replace('{{ TIP_TEXT }}', tip_text)
    except Exception as e:
        html = f"<html><body><pre>{body_plain}</pre></body></html>"

    short_sms = f"Alerta SSL ({SERVER_DOMAIN}): {title}. Restam {days_remaining} dias."
    broadcast_alert(subject, body_plain, html, short_summary=short_sms)

def send_waf_error_alert(task_name, container_name, error_details, command_output=""):
    """
    Notifica o desenvolvedor imediatamente via E-mail, Telegram e SMS se houver erro
    durante a atualização automática de CVE, Blocklist ou Reporte de Spammers do WAF.
    """
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    subject = f"[{SERVER_DOMAIN}] 🚨 ERRO WAF: Falha na tarefa {task_name} ({container_name})"

    body_plain = f"ALERTA DE SEGURANÇA E OPERAÇÃO DO WAF\n\n"
    body_plain += f"Domínio: https://{SERVER_DOMAIN}\n"
    body_plain += f"Contêiner: {container_name}\n"
    body_plain += f"Tarefa: {task_name}\n"
    body_plain += f"Data/Hora: {now_str}\n"
    body_plain += f"Diagnóstico do Erro:\n{error_details}\n\n"
    if command_output:
        body_plain += f"Saída do Comando:\n{command_output[:500]}\n\n"
    body_plain += f"Ação Recomendada:\nInspecione os logs do contêiner ({container_name}) para auditar conectividade de rede com feeds de segurança ou sintaxe do Nginx.\n"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #dc2626;">
    <div style="background-color: #dc2626; padding: 20px; text-align: center; color: white;">
      <h2 style="margin: 0; font-size: 20px;">🚨 Falha na Operação do WAF</h2>
      <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">https://{SERVER_DOMAIN}</p>
    </div>
    <div style="padding: 24px;">
      <p style="font-size: 15px; line-height: 1.5;">Ocorreu uma falha durante a execução automática de manutenção do Web Application Firewall.</p>
      <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px;">
        <tr><td style="padding: 8px 0; color: #94a3b8;"><strong>Contêiner:</strong></td><td style="color: #f1f5f9;">{container_name}</td></tr>
        <tr><td style="padding: 8px 0; color: #94a3b8;"><strong>Tarefa:</strong></td><td style="color: #ef4444;">{task_name}</td></tr>
        <tr><td style="padding: 8px 0; color: #94a3b8;"><strong>Data/Hora:</strong></td><td style="color: #f1f5f9;">{now_str}</td></tr>
      </table>
      <div style="background-color: #090d16; border-left: 4px solid #ef4444; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 13px; color: #fca5a5; overflow-x: auto; margin: 16px 0;">
        {error_details}
      </div>
      <div style="margin-top: 20px; padding: 12px; background-color: #334155; border-radius: 6px; font-size: 13px;">
        <strong>Ação Recomendada:</strong> Execute <code>docker compose logs {container_name}</code> para auditar o teste de sintaxe do Nginx ou o download das listas.
      </div>
    </div>
  </div>
</body>
</html>"""

    short_sms = f"Erro WAF ({SERVER_DOMAIN}): Falha em {task_name} no container {container_name}. Verifique os alertas."
    broadcast_alert(subject, body_plain, html, short_summary=short_sms)

def get_certificate_info():
    """
    Inspeciona os certificados locais em /certs ou os certificados do Let's Encrypt em /letsencrypt/acme.json
    Retorna: (days_remaining, expiry_date_str, issuer_str, serial_str) ou None
    """
    # 1. Tenta carregar do acme.json (Produção)
    acme_file = os.path.join(LETSENCRYPT_DIR, 'acme.json')
    cert_bytes = None

    if os.path.exists(acme_file):
        try:
            with open(acme_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                for resolver_key in data:
                    res_val = data.get(resolver_key)
                    if isinstance(res_val, dict):
                        certs_list = res_val.get('Certificates') or []
                        for entry in certs_list:
                            main_domain = entry.get('domain', {}).get('main', '')
                            if main_domain == SERVER_DOMAIN or SERVER_DOMAIN in str(entry.get('domain', {})):
                                raw_b64 = entry.get('certificate', '')
                                cert_bytes = base64.b64decode(raw_b64)
                                break
                        if cert_bytes:
                            break
        except Exception:
            pass

    # 2. Se não encontrou no acme.json, procura nos certificados de /certs (Ambiente Dev / mkcert)
    if not cert_bytes and os.path.exists(CERTS_DIR):
        for candidate in ['local-cert.pem', 'cert.pem']:
            candidate_path = os.path.join(CERTS_DIR, candidate)
            if os.path.exists(candidate_path):
                try:
                    with open(candidate_path, 'rb') as f:
                        cert_bytes = f.read()
                    break
                except Exception:
                    pass

    if not cert_bytes or not HAS_CRYPTOGRAPHY:
        return None

    try:
        cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
        # Trata datetime da expiração (compatível com cryptography novas e antigas)
        try:
            expire_utc = cert.not_valid_after_utc.replace(tzinfo=None)
        except AttributeError:
            expire_utc = cert.not_valid_after

        now = datetime.utcnow()
        days_remaining = (expire_utc - now).days
        expiry_date_str = expire_utc.strftime('%d/%m/%Y às %H:%M:%S UTC')
        issuer_parts = [f"{attr.oid._name}={attr.value}" for attr in cert.issuer if hasattr(attr, 'value')]
        issuer_str = ", ".join(issuer_parts) if issuer_parts else "Let's Encrypt / Autoridade Certificadora"
        serial_str = hex(cert.serial_number)
        return (days_remaining, expiry_date_str, issuer_str, serial_str)
    except Exception as e:
        print(f"[SSL CHECK ERROR] Falha ao decodificar certificado: {e}")
        return None

def scan_files_with_clamd():
    if not os.path.exists(SCAN_DIR):
        return

    os.makedirs(QUARANTINE_DIR, exist_ok=True)

    try:
        import pyclamd
        cd = pyclamd.ClamdNetworkSocket(CLAMAV_HOST, CLAMAV_PORT)
        if not cd.ping():
            print(f"[CLAMAV WARN] ClamAV em {CLAMAV_HOST}:{CLAMAV_PORT} ainda não está pronto para responder.")
            return

        for root, dirs, files in os.walk(SCAN_DIR):
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'rb') as f:
                        res = cd.scan_stream(f.read())
                    if res:
                        # Arquivo infectado
                        virus_info = str(res)
                        print(f"[CLAMAV] Ameaça detectada em {fpath}: {virus_info}")
                        timestamp = int(time.time())
                        quarantined_name = f"{timestamp}_{fname}.quarantine"
                        dest_path = os.path.join(QUARANTINE_DIR, quarantined_name)
                        try:
                            shutil.move(fpath, dest_path)
                            print(f"[QUARENTENA] Arquivo movido: {fpath} -> {dest_path}")
                        except Exception as move_err:
                            dest_path = f"Falha ao mover: {fpath} ({move_err})"
                        send_antivirus_alert(fpath, virus_info, str(res), dest_path)
                except Exception as file_err:
                    pass
    except Exception as e:
        # Fallback para clamscan local se falhar
        try:
            cmd = ["clamscan", "-r", "--infected", "--no-summary", SCAN_DIR]
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
            if process.returncode == 1:
                for line in process.stdout.splitlines():
                    if "FOUND" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            fpath = parts[0].strip()
                            virus_info = parts[1].replace("FOUND", "").strip()
                            dest_path = os.path.join(QUARANTINE_DIR, f"{int(time.time())}_{os.path.basename(fpath)}.quarantine")
                            try:
                                shutil.move(fpath, dest_path)
                            except Exception:
                                pass
                            send_antivirus_alert(fpath, virus_info, process.stdout, dest_path)
        except Exception as fallback_err:
            print(f"[CLAMAV ERROR] Falha no scanner: {e} / {fallback_err}")

def get_cpu_percent(stats):
    try:
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        cpu_percent = 0.0
        if system_delta > 0.0 and cpu_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', [1])) * 100.0
        return cpu_percent
    except Exception:
        return 0.0

def get_mem_stats(stats):
    try:
        mem_usage = stats['memory_stats']['usage']
        mem_limit = stats['memory_stats']['limit']
        mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0.0
        usage_mb = mem_usage / (1024 * 1024)
        limit_mb = mem_limit / (1024 * 1024)
        return mem_percent, f"{usage_mb:.0f} MB / {limit_mb:.0f} MB"
    except Exception:
        return 0.0, "N/A"

def get_disk_stats(path):
    try:
        total, used, free = shutil.disk_usage(path)
        percent = (used / total) * 100.0 if total > 0 else 0.0
        used_gb = used / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        return percent, f"{used_gb:.1f} GB / {total_gb:.1f} GB"
    except Exception:
        return 0.0, "N/A"

def monitor_loop():
    print("Iniciando sentinela: CPU, Memória RAM, Disco (HD), ClamAV e Certificados SSL...")
    alerted_cpu = {}
    alerted_mem = {}
    last_disk_alert = 0
    last_antivirus_scan = 0
    last_ssl_check = 0
    last_known_serial = None
    ssl_alerted_30 = False
    ssl_alerted_10 = False
    last_logs_purge = 0
    last_blocklist_update = time.time()
    last_spam_report = time.time()

    while True:
        now = time.time()

        # 1. Monitoramento de Certificados SSL/TLS (Executado a cada 1 hora ou no boot)
        if now - last_ssl_check >= 3600 or last_ssl_check == 0:
            ssl_info = get_certificate_info()
            if ssl_info:
                days, exp_str, issuer, serial = ssl_info

                # Detecta se o certificado foi renovado (o serial do certificado mudou)
                if last_known_serial is not None and serial != last_known_serial:
                    print(f"[SSL RENEWED] Certificado foi renovado! Novo serial: {serial}")
                    send_ssl_notification('renewed', days, exp_str, issuer, serial)
                    ssl_alerted_30 = False
                    ssl_alerted_10 = False

                last_known_serial = serial

                # Alerta de 10 dias
                if days <= 10:
                    if not ssl_alerted_10:
                        send_ssl_notification('warning_10', days, exp_str, issuer, serial)
                        ssl_alerted_10 = True
                # Alerta de 30 dias
                elif days <= 30:
                    if not ssl_alerted_30:
                        send_ssl_notification('warning_30', days, exp_str, issuer, serial)
                        ssl_alerted_30 = True

            last_ssl_check = now

        # 2. Verifica Disco / Volumes do Host (SCAN_DIR e QUARANTINE_DIR)
        disk_pct, disk_str = get_disk_stats(SCAN_DIR)
        if disk_pct >= DISK_THRESHOLD:
            if now - last_disk_alert > 1800:
                recom = "Libere espaço em disco apagando arquivos temporários ou backups antigos em /scandata ou /quarantine."
                details = f"Uso do volume de dados da aplicação: {disk_pct:.1f}% ({disk_str})"
                send_resource_alert('disk', 'Volume de Armazenamento (/scandata)', 0.0, 0.0, 'N/A', disk_pct, disk_str, 'Diagnóstico do Sistema de Arquivos', details, recom)
                last_disk_alert = now

        # 3. Verifica CPU e RAM de cada contêiner Docker
        try:
            for container in client.containers.list():
                stats = container.stats(stream=False)
                cpu_percent = get_cpu_percent(stats)
                mem_percent, mem_usage_str = get_mem_stats(stats)

                # Alerta de CPU
                if cpu_percent >= CPU_THRESHOLD:
                    last_alert = alerted_cpu.get(container.name, 0)
                    if now - last_alert > 600:
                        try:
                            top_result = container.top()
                            processes_info = "\n".join(["\t".join(row) for row in top_result['Processes']])
                        except Exception as e:
                            processes_info = "Não foi possível obter processos: " + str(e)
                        recom = f"Considere escalar as réplicas em APP_REPLICAS no .env ou auditar requisições em loop no WAF."
                        send_resource_alert('cpu', container.name, cpu_percent, mem_percent, mem_usage_str, disk_pct, disk_str, 'Processos Ativos no Momento do Alerta', processes_info, recom)
                        alerted_cpu[container.name] = now

                # Alerta de Memória RAM
                if mem_percent >= MEM_THRESHOLD:
                    last_alert = alerted_mem.get(container.name, 0)
                    if now - last_alert > 600:
                        try:
                            top_result = container.top()
                            processes_info = "\n".join(["\t".join(row) for row in top_result['Processes']])
                        except Exception as e:
                            processes_info = "Não foi possível obter processos: " + str(e)
                        recom = f"Contêiner atingiu limite elevado de memória. Verifique vazamentos em processos filhos ou aumente o limite de RAM do Docker."
                        send_resource_alert('memory', container.name, cpu_percent, mem_percent, mem_usage_str, disk_pct, disk_str, 'Processos Consumindo Memória', processes_info, recom)
                        alerted_mem[container.name] = now

        except Exception as e:
            print(f"[MONITOR ERROR] Erro durante o monitoramento de contêineres: {str(e)}")

        # 4. Scanner do ClamAV roda a cada 60 segundos
        if now - last_antivirus_scan >= 60:
            scan_files_with_clamd()
            last_antivirus_scan = now

        # 5. Atualização Periódica de Threat Intelligence / Blocklist no WAF (A cada 12 horas: 43200s)
        if now - last_blocklist_update >= 43200:
            try:
                for c in client.containers.list():
                    if 'waf' in c.name.lower():
                        print(f"[WAF AUTO-TASK] Atualizando listas de bloqueio (StopForumSpam/FireHOL/AbuseIPDB) em {c.name}...")
                        exec_res = c.exec_run("sh /scripts/update_blocklist.sh")
                        out_str = exec_res.output.decode('utf-8', errors='ignore') if exec_res.output else ""
                        if exec_res.exit_code != 0:
                            print(f"[WAF AUTO-TASK ERRO] Falha ao atualizar listas em {c.name} (exit_code={exec_res.exit_code})")
                            send_waf_error_alert("Atualização de Listas de Ameaças (update_blocklist.sh)", c.name, f"O script retornou código de erro {exec_res.exit_code}.", out_str)
                        else:
                            print(f"[WAF AUTO-TASK] Concluído em {c.name} com sucesso.")
                last_blocklist_update = now
            except Exception as e:
                print(f"[WAF AUTO-TASK ERROR] Erro durante chamada Docker da blocklist: {str(e)}")
                send_waf_error_alert("Execução de Blocklist WAF", "Cluster WAF", f"Exceção Docker: {str(e)}")

        # 6. Reporte Automático de Atacantes e Spammers (A cada 1 hora: 3600s)
        if now - last_spam_report >= 3600:
            try:
                for c in client.containers.list():
                    if 'waf' in c.name.lower():
                        print(f"[WAF AUTO-TASK] Reportando invasores capturados no Honeypot em {c.name} ao StopForumSpam...")
                        exec_res = c.exec_run("sh /scripts/report_spam.sh")
                        out_str = exec_res.output.decode('utf-8', errors='ignore') if exec_res.output else ""
                        if exec_res.exit_code != 0:
                            print(f"[WAF AUTO-TASK ERRO] Falha no envio de spammers em {c.name} (exit_code={exec_res.exit_code})")
                            send_waf_error_alert("Reporte de Spammers (report_spam.sh)", c.name, f"O script retornou código de erro {exec_res.exit_code}.", out_str)
                        else:
                            print(f"[WAF AUTO-TASK] Reporte concluído em {c.name} com sucesso.")
                last_spam_report = now
            except Exception as e:
                print(f"[WAF AUTO-TASK ERROR] Erro durante chamada Docker de reporte de spam: {str(e)}")
                send_waf_error_alert("Envio de Spammers WAF", "Cluster WAF", f"Exceção Docker: {str(e)}")

        # 7. Expurgo e retenção de logs (/logs/) para até 60 dias (Executado 1x por dia ou no boot)
        if now - last_logs_purge >= 86400 or last_logs_purge == 0:
            purge_old_alert_logs()
            last_logs_purge = now

        time.sleep(30)

if __name__ == '__main__':
    monitor_loop()

