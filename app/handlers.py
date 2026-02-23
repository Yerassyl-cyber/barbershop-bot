from .telegram_api import tg_send, tg_edit
from .state import get_draft, clear_draft  # немесе clear_booking_fields
from .config import ADMIN_CHAT_ID
import asyncio
from datetime import datetime, timedelta
from .db import (
    get_salon_by_start_code,
    get_masters_by_salon,
    get_services_by_salon,
    insert_booking,
    is_slot_taken,
)

TIMES = ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30"]

def main_menu_kb():
    return {
        "inline_keyboard": [
            [{"text": "📅 Запись", "callback_data": "menu:book"}],
            [{"text": "💰 Бағалар", "callback_data": "menu:prices"}],
        ]
    }

def masters_kb(salon_id: int):
    masters = get_masters_by_salon(salon_id)
    rows = [[{"text": f"✂️ {name}", "callback_data": f"master:{mid}"}] for (mid, name) in masters]
    rows.append([{"text": "⬅️ Артқа", "callback_data": "menu:back"}])
    return {"inline_keyboard": rows}

def services_kb(salon_id: int):
    services = get_services_by_salon(salon_id)
    rows = [[{"text": title, "callback_data": f"service:{sid}"}] for (sid, title, price) in services]
    rows.append([{"text": "⬅️ Артқа", "callback_data": "menu:book"}])
    return {"inline_keyboard": rows}

def days_kb():
    rows = []
    today = datetime.now()
    for i in range(5):
        d = today + timedelta(days=i)
        label = d.strftime("%a %d.%m")
        iso = d.strftime("%Y-%m-%d")
        rows.append([{"text": label, "callback_data": f"day:{iso}"}])
    rows.append([{"text": "⬅️ Артқа", "callback_data": "back:services"}])
    return {"inline_keyboard": rows}

def times_kb():
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

def _find_service(services, service_id: str):
    # services: list[(sid, title, price)]
    for sid, title, price in services:
        if str(sid) == str(service_id):
            return title, price
    return "?", 0

async def handle_start(chat_id: int, start_payload: str | None = None):
    clear_draft(chat_id)
    draft = get_draft(chat_id)

    if start_payload:
        salon = await asyncio.to_thread(get_salon_by_start_code, start_payload)
        if salon:
            salon_id, salon_name = salon
            draft.salon_id = int(salon_id)

            await tg_send(chat_id, f"✂️ {salon_name}\n\nТаңдаңыз:", reply_markup=main_menu_kb())
            return

    await tg_send(
        chat_id,
        "Салон сілтемесі арқылы кіріңіз.\nМысалы: t.me/yourbot?start=salon_1"
    )

async def handle_prices(chat_id: int, message_id: int):
    draft = get_draft(chat_id)
    if not draft.salon_id:
        await tg_edit(chat_id, message_id, "Салон таңдалмаған. /start арқылы кіріңіз.")
        return

    services = await asyncio.to_thread(get_services_by_salon, draft.salon_id)

    text = "Бағалар:\n"
    for sid, title, price in services:
        text += f"- {title}: {price} тг\n"

    await tg_edit(chat_id, message_id, text + "\n⬅️ Артқа қайтайық:", reply_markup=main_menu_kb())

async def handle_callback(chat_id: int, data: str, message_id: int):
    draft = get_draft(chat_id)

    if data == "menu:prices":
        await handle_prices(chat_id, message_id)
        return

    if data == "menu:book":
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "Салон таңдалмаған. /start link арқылы кіріңіз.")
            return

        # салонды сақтап, қалғанын тазалау
        salon_id = draft.salon_id
        clear_draft(chat_id)
        draft = get_draft(chat_id)
        draft.salon_id = salon_id

        await tg_edit(chat_id, message_id, "Мастерді таңдаңыз:", reply_markup=masters_kb(draft.salon_id))
        return

    if data == "menu:back":
        await tg_edit(chat_id, message_id, "Таңдаңыз:", reply_markup=main_menu_kb())
        return

    if data.startswith("master:"):
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "Салон таңдалмаған. /start арқылы кіріңіз.")
            return
        master_id = data.split(":")[1]
        draft.master_id = str(master_id)
        await tg_edit(chat_id, message_id, "Қызметті таңдаңыз:", reply_markup=services_kb(draft.salon_id))
        return

    if data.startswith("service:"):
        service_id = data.split(":")[1]
        draft.service_id = str(service_id)
        await tg_edit(chat_id, message_id, "Күнді таңдаңыз:", reply_markup=days_kb())
        return

    if data == "back:services":
        await tg_edit(chat_id, message_id, "Қызметті таңдаңыз:", reply_markup=services_kb(draft.salon_id))
        return

    if data.startswith("day:"):
        day = data.split(":", 1)[1]
        draft.day = day
        await tg_edit(chat_id, message_id, "Уақытты таңдаңыз:", reply_markup=times_kb())
        return

    if data == "back:days":
        await tg_edit(chat_id, message_id, "Күнді таңдаңыз:", reply_markup=days_kb())
        return

    if data.startswith("time:"):
        t = data.split(":", 1)[1]
        draft.time = t

        # summary + confirm
        masters = await asyncio.to_thread(get_masters_by_salon, draft.salon_id)
        master_name = next((name for (mid, name) in masters if str(mid) == str(draft.master_id)), "?")

        services = await asyncio.to_thread(get_services_by_salon, draft.salon_id)
        service_name, price = _find_service(services, draft.service_id)

        dt = datetime.strptime(draft.day, "%Y-%m-%d")
        pretty_day = dt.strftime("%d.%m.%Y")

        summary = (
            "Тапсырысыңыз:\n"
            f"👤 Мастер: {master_name}\n"
            f"🛠 Қызмет: {service_name}\n"
            f"📅 Күн: {pretty_day}\n"
            f"⏰ Уақыт: {draft.time}\n"
            f"💳 Баға: {price} тг\n\n"
            "Растаймыз ба?"
        )

        # price-ты draft-қа сақтап қойсаң да болады (қаласаң)
        draft.price = price  # Draft-та price field болса

        await tg_edit(chat_id, message_id, summary, reply_markup=confirm_kb())
        return

    if data == "confirm:yes":
        if not (draft.salon_id and draft.master_id and draft.service_id and draft.day and draft.time):
            await tg_edit(chat_id, message_id, "⚠️ Дерек толық емес. Қайтадан бастап көріңіз.", reply_markup=main_menu_kb())
            return

        services = await asyncio.to_thread(get_services_by_salon, draft.salon_id)
        service_name, price = _find_service(services, draft.service_id)

        masters = await asyncio.to_thread(get_masters_by_salon, draft.salon_id)
        master_name = next((name for (mid, name) in masters if str(mid) == str(draft.master_id)), "?")

        taken = await asyncio.to_thread(
            is_slot_taken,
            int(draft.salon_id),
            str(draft.master_id),
            str(draft.day),
            str(draft.time),
        )
        if taken:
            await tg_edit(chat_id, message_id, "⚠️ Бұл уақыт бос емес екен. Басқа уақыт таңдаңыз:", reply_markup=times_kb())
            return

        booking_id = await asyncio.to_thread(
            insert_booking,
            chat_id,
            int(draft.salon_id),
            str(draft.master_id),
            str(draft.service_id),
            str(draft.day),
            str(draft.time),
            int(price),
        )

        await tg_edit(
            chat_id, message_id,
            f"✅ Жазылдыңыз! (№{booking_id})\nАдмин жақында хабарласады.\n\nҚайта меню:",
            reply_markup=main_menu_kb()
        )

        if ADMIN_CHAT_ID:
            admin_text = (
                f"🆕 Жаңа запись! №{booking_id}\n\n"
                f"👤 Клиент chat_id: {chat_id}\n"
                f"🏠 Салон ID: {draft.salon_id}\n"
                f"✂️ Мастер: {master_name}\n"
                f"🛠 Қызмет: {service_name}\n"
                f"📅 Күн: {draft.day}\n"
                f"⏰ Уақыт: {draft.time}\n"
                f"💳 Баға: {price} тг\n"
                f"Статус: pending"
            )
            await tg_send(ADMIN_CHAT_ID, admin_text)

        clear_draft(chat_id)
        return

    if data == "confirm:no":
        await tg_edit(chat_id, message_id, "❌ Болдырылмады.\n\nҚайта меню:", reply_markup=main_menu_kb())
        clear_draft(chat_id)
        return

    await tg_edit(chat_id, message_id, "Түсінбедім. Мәзірден таңдаңыз:", reply_markup=main_menu_kb())