from fastapi import FastAPI, Request, Header, HTTPException

from .config import WEBHOOK_SECRET
from .telegram_api import init_client, close_client, tg_answer_callback
from .handlers import handle_start, handle_callback
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
        # ✅ бұл “баяу жауап” проблемасын шешеді
        await tg_answer_callback(cb["id"])

        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]   # ✅ осы керек
        data = cb.get("data", "")
        await handle_callback(chat_id, data, msg_id)

        return {"ok": True}

    msg = update.get("message")
    if msg and "text" in msg:
        chat_id = msg["chat"]["id"]
        text = msg["text"]

        if text.startswith("/start"):
            await handle_start(chat_id)
        else:
        # Қазір сенде reply-keyboard жоқ, бәрі inline.
        # Сондықтан жай менюді қайта көрсетеміз:
               await handle_start(chat_id)


    return {"ok": True}
