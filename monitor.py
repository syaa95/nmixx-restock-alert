"""NMIXX restock watcher. Python standard library only; credentials via env."""
import json
import os
import smtplib
import ssl
import time
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

HANDLE = "strange-muse-strange-ver-vinyl"
URL = "https://nmixxshopus.com/products/" + HANDLE
STATE = Path("stock-state.json")


def fetch_product():
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                URL + ".js", headers={"User-Agent": "NMIXX-Restock-Monitor/1.0",
                                       "Accept": "application/json", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.load(response)
            validate_product(data)
            return data
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def validate_product(data):
    if not isinstance(data, dict) or data.get("handle") != HANDLE:
        raise ValueError("Unexpected product response; previous stock state preserved")
    if type(data.get("available")) is not bool or not data.get("variants"):
        raise ValueError("Missing stock information; previous stock state preserved")
    if any(type(v.get("available")) is not bool for v in data["variants"]):
        raise ValueError("Invalid variant availability")
    if data["available"] != any(v["available"] for v in data["variants"]):
        raise ValueError("Inconsistent product and variant availability")


def send_mail(subject, body):
    sender = os.environ["GMAIL_USER"].strip()
    recipient = os.environ["ALERT_TO"].strip()
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "").strip()
    if not sender or not recipient or not password:
        raise ValueError("Mail configuration is incomplete")
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    # Do not retry SMTP: a timeout after acceptance could send duplicates.
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30,
                          context=ssl.create_default_context()) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)


def run(mode="check"):
    if mode not in {"check", "inspect", "test-email"}:
        raise ValueError("Unknown mode")
    data = fetch_product()
    now = datetime.now(timezone.utc)
    available = data["available"]
    print("Inventory checked (UTC):", now.isoformat())
    print("Product:", data["title"])
    print("Available:", available)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as output:
            output.write(f"## NMIXX inventory check\n\nChecked: {now.isoformat()}\n\n"
                         f"Available: **{available}**\n\n[Product]({URL})\n")
    if mode == "inspect":
        print("Inspect only: no mail sent and no state changed.")
        return
    required = ("GMAIL_USER", "GMAIL_APP_PASSWORD", "ALERT_TO")
    if any(not os.environ.get(key, "").strip() for key in required):
        raise ValueError("Set GMAIL_USER, GMAIL_APP_PASSWORD and ALERT_TO in Actions Secrets")
    body = (f"商品：{data['title']}\n当前状态：{'可购买' if available else '售罄'}\n"
            f"检查时间（UTC）：{now.isoformat()}\n商品链接：{URL}\n\n"
            "店铺注明仅限美国销售。库存可能很快变化，请打开链接确认。\n")
    if mode == "test-email":
        send_mail("[测试] NMIXX 补货提醒邮件通道", "这是测试邮件，不代表商品补货。\n\n" + body)
        print("Test email accepted by mail server; inventory state unchanged.")
        return
    previous = None
    if STATE.exists():
        previous = json.loads(STATE.read_text(encoding="utf-8"))
        if previous.get("url") != URL or type(previous.get("available")) is not bool:
            raise ValueError("Invalid saved state; refusing to overwrite it")
    if available and (previous is None or not previous["available"]):
        send_mail("[补货提醒] NMIXX Strange Muse 黑胶可购买", body)
        print("Restock email accepted by mail server.")
    elif previous is None:
        send_mail("[已启用] NMIXX 补货监控", "云端监控已完成首次检查；这不是补货通知。\n\n" + body)
        print("Activation email accepted by mail server.")
    else:
        print("No restock transition; no email sent.")
    # Daily checkpoint helps users audit that the monitor remains healthy.
    state = {"url": URL, "available": available, "last_success_date_utc": now.date().isoformat()}
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        run(os.environ.get("MODE", "check"))
    except Exception as error:
        # Avoid logging SMTP response bodies or credentials in public job logs.
        print(f"::error::Monitor failed ({type(error).__name__}). Check inventory access and mail Secrets; saved state was not advanced.")
        raise SystemExit(1)
