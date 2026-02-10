import os
import httpx
from fastapi import FastAPI, Request, Header, HTTPException

app = FastAPI()

BOT_TOKEN = os.getenv("BARBER_BOT_TOKEN", "")
WEBHOOK_SECRET = os.getenv("BARBER_WEBHOOK_SECRET", "")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


@app.get("/health")
def health():
    return {"status": "ok"}


async def tg_send(chat_id: int, text: str, reply_markup: dict | None = None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        r.raise_for_status()


@app.post("/telegram/barber/webhook")
async def barber_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None)
):
    # webhook security
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    update = await request.json()
    cb = update.get("callback_query")
    if cb:
        chat_id = cb["message"]["chat"]["id"]
        data = cb.get("data", "")

        if data == "menu:prices":
            await tg_send(chat_id, "Бағалар:\n- Стрижка: 4000\n- Борода: 3000\n- Стрижка+борода: 6500")
        elif data == "menu:book":
            await tg_send(chat_id, "Ок! Енді мастер таңдаймыз (келесі қадамда).")
        return {"ok": True}

    msg = update.get("message")
    if msg and "text" in msg:
        chat_id = msg["chat"]["id"]
        text = msg["text"]

        if text.startswith("/start"):
            kb = {
                "inline_keyboard": [
                    [{"text": "📅 Запись", "callback_data": "menu:book"}],
                    [{"text": "💰 Бағалар", "callback_data": "menu:prices"}],
                ]
            }
            await tg_send(chat_id, "Сәлем! ✂️ SheberCut\n\nТаңдаңыз:", reply_markup=kb)

    return {"ok": True}


