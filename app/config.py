# app/config.py
import os

BOT_TOKEN = os.getenv("BARBER_BOT_TOKEN", "")
WEBHOOK_SECRET = os.getenv("BARBER_WEBHOOK_SECRET", "")
SQL_CONN_STR = os.getenv("SQL_CONN_STR", "")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")