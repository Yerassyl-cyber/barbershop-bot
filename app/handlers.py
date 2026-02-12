from .telegram_api import tg_send
from .state import get_draft, clear_draft
from .config import ADMIN_CHAT_ID
import asyncio
from .db import insert_booking, is_slot_taken
from .telegram_api import tg_edit


MASTERS = {
    "1": "Асан",
    "2": "Дәурен",
}

SERVICES = {
    "haircut": ("✂️ Стрижка", 4000),
    "beard": ("🧔 Борода", 3000),
    "combo": ("🔥 Стрижка+борода", 6500),
}

DAYS = ["Бүгін", "Ертең", "Сәрсенбі", "Бейсенбі"]  # кейін нақты күнге ауыстырамыз
TIMES = ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30"]  # үлгі

def main_menu_kb():
    return {
        "inline_keyboard": [
            [{"text": "📅 Запись", "callback_data": "menu:book"}],
            [{"text": "💰 Бағалар", "callback_data": "menu:prices"}],
        ]
    }

def masters_kb():
    return {
        "inline_keyboard": [
            [{"text": "✂️ Асан", "callback_data": "master:1"}],
            [{"text": "✂️ Дәурен", "callback_data": "master:2"}],
            [{"text": "⬅️ Артқа", "callback_data": "menu:back"}],
        ]
    }

def services_kb():
    return {
        "inline_keyboard": [
            [{"text": SERVICES["haircut"][0], "callback_data": "service:haircut"}],
            [{"text": SERVICES["beard"][0], "callback_data": "service:beard"}],
            [{"text": SERVICES["combo"][0], "callback_data": "service:combo"}],
            [{"text": "⬅️ Артқа", "callback_data": "menu:book"}],
        ]
    }

def days_kb():
    return {
        "inline_keyboard": [
            [{"text": d, "callback_data": f"day:{d}"}] for d in DAYS
        ] + [[{"text": "⬅️ Артқа", "callback_data": "back:services"}]]
    }

def times_kb():
    # 2 баған қылып шығарайық
    rows = []
    for i in range(0, len(TIMES), 2):
        row = [{"text": TIMES[i], "callback_data": f"time:{TIMES[i]}"}]
        if i + 1 < len(TIMES):
            row.append({"text": TIMES[i+1], "callback_data": f"time:{TIMES[i+1]}"} )
        rows.append(row)
    rows.append([{"text": "⬅️ Артқа", "callback_data": "back:days"}])
    return {"inline_keyboard": rows}

def confirm_kb():
    return {
        "inline_keyboard": [
            [{"text": "✅ Растау", "callback_data": "confirm:yes"}],
            [{"text": "❌ Болдырмау", "callback_data": "confirm:no"}],
        ]
    }

async def handle_start(chat_id: int):
    await tg_send(chat_id, "Сәлем! ✂️ SheberCut\n\nТаңдаңыз:", reply_markup=main_menu_kb())

async def handle_prices(chat_id: int, message_id: int):
    text = "Бағалар:\n"
    for k, (name, price) in SERVICES.items():
        text += f"- {name}: {price} тг\n"
    await tg_edit(chat_id, message_id, text + "\n⬅️ Артқа қайтайық:", reply_markup=main_menu_kb())


async def handle_callback(chat_id: int, data: str, message_id: int):
    draft = get_draft(chat_id)

    if data == "menu:prices":
        await handle_prices(chat_id, message_id)   # ✅ edit арқылы
        return


    if data == "menu:book":
        clear_draft(chat_id)
        await tg_edit(chat_id, "Мастерді таңдаңыз:", reply_markup=masters_kb())
        return

    if data == "menu:back":
        await tg_edit(chat_id, "Таңдаңыз:", reply_markup=main_menu_kb())
        return

    if data.startswith("master:"):
        master_id = data.split(":")[1]
        draft.master_id = master_id
        await tg_edit(chat_id, f"Мастер: {MASTERS.get(master_id,'?')}\n\nҚызметті таңдаңыз:", reply_markup=services_kb())
        return

    if data.startswith("service:"):
        service_id = data.split(":")[1]
        draft.service_id = service_id
        await tg_edit(chat_id, "Күнді таңдаңыз:", reply_markup=days_kb())
        return

    if data == "back:services":
        await tg_edit(chat_id, "Қызметті таңдаңыз:", reply_markup=services_kb())
        return

    if data.startswith("day:"):
        day = data.split(":", 1)[1]
        draft.day = day
        await tg_edit(chat_id, "Уақытты таңдаңыз:", reply_markup=times_kb())
        return

    if data == "back:days":
        await tg_edit(chat_id, "Күнді таңдаңыз:", reply_markup=days_kb())
        return

    if data.startswith("time:"):
        t = data.split(":", 1)[1]
        draft.time = t

        master_name = MASTERS.get(draft.master_id or "", "?")
        service_name, price = SERVICES.get(draft.service_id or "", ("?", 0))

        summary = (
            "Тапсырысыңыз:\n"
            f"👤 Мастер: {master_name}\n"
            f"🛠 Қызмет: {service_name}\n"
            f"📅 Күн: {draft.day}\n"
            f"⏰ Уақыт: {draft.time}\n"
            f"💳 Баға: {price} тг\n\n"
            "Растаймыз ба?"
        )
        await tg_edit(chat_id, summary, reply_markup=confirm_kb())
        return

    if data == "confirm:yes":
        master_name = MASTERS.get(draft.master_id or "", "?")
        service_name, price = SERVICES.get(draft.service_id or "", ("?", 0))

    # ✅ Слот бос па тексереміз
        taken = await asyncio.to_thread(
        is_slot_taken,
        draft.master_id or "",
        draft.day or "",
        draft.time or ""
        )
        if taken:
           await tg_edit(chat_id, "⚠️ Бұл уақыт бос емес екен. Басқа уақыт таңдаңыз:", reply_markup=times_kb())
           return

        # ✅ SQL-ға сақтаймыз (pyodbc sync болғандықтан thread)
        booking_id = await asyncio.to_thread(
            insert_booking,
            chat_id,
            draft.master_id or "",
            draft.service_id or "",
            draft.day or "",
            draft.time or "",
            price
        )

    # Клиентке жауап
    await tg_send(
        chat_id,
        f"✅ Жазылдыңыз! (№{booking_id})\nАдмин жақында хабарласады.\n\nҚайта меню:",
        reply_markup=main_menu_kb()
    )

    # Админге хабарлама
    if ADMIN_CHAT_ID != 0:
        admin_text = (
            f"🆕 Жаңа запись! №{booking_id}\n\n"
            f"👤 Клиент chat_id: {chat_id}\n"
            f"✂️ Мастер: {master_name}\n"
            f"🛠 Қызмет: {service_name}\n"
            f"📅 Күн: {draft.day}\n"
            f"⏰ Уақыт: {draft.time}\n"
            f"💳 Баға: {price} тг\n"
            f"Статус: pending"
        )
        await tg_edit(ADMIN_CHAT_ID, admin_text)
    else:
        print("⚠ ADMIN_CHAT_ID орнатылмаған!")

    clear_draft(chat_id)
    return


    

    if data == "confirm:no":
        await tg_edit(chat_id, "❌ Болдырылмады.\n\nҚайта меню:", reply_markup=main_menu_kb())
        clear_draft(chat_id)
        return

    await tg_edit(chat_id, "Түсінбедім. Мәзірден таңдаңыз:", reply_markup=main_menu_kb())
