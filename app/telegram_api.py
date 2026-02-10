import httpx
from .config import TELEGRAM_API

client: httpx.AsyncClient | None = None

async def init_client():
    global client
    client = httpx.AsyncClient(timeout=10)

async def close_client():
    global client
    if client:
        await client.aclose()
        client = None

async def tg_send(chat_id: int, text: str, reply_markup: dict | None = None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    r = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
    r.raise_for_status()

async def tg_answer_callback(callback_query_id: str, text: str | None = None):
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    r = await client.post(f"{TELEGRAM_API}/answerCallbackQuery", json=payload)
    r.raise_for_status()
