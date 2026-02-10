# app/config.py
import os

BOT_TOKEN = os.getenv("BARBER_BOT_TOKEN", "")
WEBHOOK_SECRET = os.getenv("BARBER_WEBHOOK_SECRET", "")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
