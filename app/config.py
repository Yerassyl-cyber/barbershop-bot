# app/config.py
import os

BOT_TOKEN = os.getenv("BARBER_BOT_TOKEN", "")
WEBHOOK_SECRET = os.getenv("BARBER_WEBHOOK_SECRET", "")
SQL_CONN_STR = os.getenv("SQL_CONN_STR", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
