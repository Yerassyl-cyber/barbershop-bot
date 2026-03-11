from fastapi import FastAPI, Request, Header, HTTPException

from .config import WEBHOOK_SECRET
from .telegram_api import init_client, close_client, tg_answer_callback
from .handlers import handle_start, handle_callback,handle_message
from .db import init_db

app = FastAPI()

    
@app.get("/")
def root():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    await init_client()
    init_db()   # ✅ таблица автомат жасалады

    

@app.on_event("shutdown")
async def on_shutdown():
    await close_client()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/telegram/barber/webhook")
async def barber_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # webhook security
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    update = await request.json()

    cb = update.get("callback_query")
    if cb:
        await tg_answer_callback(cb["id"])

        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        data = cb.get("data", "")

        try:
            await handle_callback(chat_id, data, msg_id)
        except Exception as e:
            print(f"CALLBACK ERROR: {e}")

        return {"ok": True}

    msg = update.get("message")
    if msg:
        chat_id = msg["chat"]["id"]
        text = msg.get("text")

        if text and text.startswith("/start"):
            parts = text.split(" ", 1)
            payload = parts[1].strip() if len(parts) > 1 else None
            await handle_start(chat_id, payload)
        else:
            await handle_message(chat_id, text, msg)
        

    return {"ok": True}
