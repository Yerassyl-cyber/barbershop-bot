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


async def tg_send(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        })
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

    msg = update.get("message")
    if msg and "text" in msg:
        chat_id = msg["chat"]["id"]
        text = msg["text"]

        if text.startswith("/start"):
            await tg_send(chat_id, "Сәлем! ✂️ SheberCut_bot жұмыс істеп тұр. Запись жасау жақында қосылады 🙂")

    return {"ok": True}
