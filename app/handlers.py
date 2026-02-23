from .telegram_api import tg_send, tg_edit
from .state import get_draft, clear_draft  # немесе clear_booking_fields
from .db import get_salon_admin_chat_id
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
            row.append({"text": TIMES[i + 1], "callback_data": f"time:{TIMES[i + 1]}"} )
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

    # ----------------------------
    # MAIN MENU
    # ----------------------------
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

    # ----------------------------
    # BOOKING FLOW
    # ----------------------------
    if data.startswith("master:"):
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "Салон таңдалмаған. /start арқылы кіріңіз.")
            return

        master_id = data.split(":", 1)[1]
        draft.master_id = str(master_id)
        await tg_edit(chat_id, message_id, "Қызметті таңдаңыз:", reply_markup=services_kb(draft.salon_id))
        return

    if data.startswith("service:"):
        service_id = data.split(":", 1)[1]
        draft.service_id = str(service_id)
        await tg_edit(chat_id, message_id, "Күнді таңдаңыз:", reply_markup=days_kb())
        return

    if data == "back:services":
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "Салон таңдалмаған. /start арқылы кіріңіз.", reply_markup=main_menu_kb())
            return
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

    # ----------------------------
    # TIME -> IMMEDIATE BOOKING (логика өзгермейді)
    # ----------------------------
# ----------------------------
# TIME -> SHOW CONFIRMATION (растау арқылы бронь)
# ----------------------------
    if data.startswith("time:"):
        t = data.split(":", 1)[1]
        draft.time = t

        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "Салон таңдалмаған. /start арқылы кіріңіз.", reply_markup=main_menu_kb())
            return

    # master name
        masters = await asyncio.to_thread(get_masters_by_salon, draft.salon_id)
        master_name = next((name for (mid, name) in masters if str(mid) == str(draft.master_id)), "?")

    # service title + price
        services = await asyncio.to_thread(get_services_by_salon, draft.salon_id)
        service_row = next(
            ((sid, title, price) for (sid, title, price) in services if str(sid) == str(draft.service_id)),
            None
            )
        if not service_row:
            await tg_edit(chat_id, message_id, "Қызмет табылмады. Қайта таңдаңыз.", reply_markup=services_kb(draft.salon_id))
            return

        _, service_name, price = service_row

    # slot check
        taken = await asyncio.to_thread(
            is_slot_taken,
            draft.salon_id,
            draft.master_id or "",
            draft.day or "",
            draft.time or ""
            )
        if taken:
            await tg_edit(chat_id, message_id, "⚠️ Бұл уақыт бос емес. Басқа уақыт таңдаңыз:", reply_markup=times_kb())
            return

    # ✅ CONFIRM SCREEN
        text = (
        "Растайсыз ба?\n\n"
        f"✂️ Мастер: {master_name}\n"
        f"🛠 Қызмет: {service_name}\n"
        f"📅 Күн: {draft.day}\n"
        f"⏰ Уақыт: {draft.time}\n"
        f"💳 Баға: {price} тг"
        )
        await tg_edit(chat_id, message_id, text, reply_markup=confirm_kb())
        return

    # ----------------------------
    # CONFIRMATION (қалсын, бірақ дұрыс жұмыс істесін)
    # ЕСКЕРТУ: қазіргі логикада бұл шақырылмауы мүмкін
    # ----------------------------
    if data == "confirm:yes":
        if not (draft.salon_id and draft.master_id and draft.service_id and draft.day and draft.time):
            await tg_edit(chat_id, message_id, "⚠️ Дерек толық емес. Қайтадан бастап көріңіз.", reply_markup=main_menu_kb())
            return

        services = await asyncio.to_thread(get_services_by_salon, draft.salon_id)
        service_row = next(((sid, title, price) for (sid, title, price) in services if str(sid) == str(draft.service_id)), None)
        if not service_row:
            await tg_edit(chat_id, message_id, "Қызмет табылмады. Қайта таңдаңыз.", reply_markup=services_kb(draft.salon_id))
            return
        _, service_name, price = service_row

        masters = await asyncio.to_thread(get_masters_by_salon, draft.salon_id)
        master_name = next((name for (mid, name) in masters if str(mid) == str(draft.master_id)), "?")

        taken = await asyncio.to_thread(
            is_slot_taken,
            draft.salon_id,
            draft.master_id,
            draft.day,
            draft.time,
            )
        if taken:
            await tg_edit(chat_id, message_id, "⚠️ Бұл уақыт бос емес екен. Басқа уақыт таңдаңыз:", reply_markup=times_kb())
            return

        booking_id = await asyncio.to_thread(
            insert_booking,
            draft.salon_id,
            chat_id,
            draft.master_id,
            draft.service_id,
            draft.day,
            draft.time,
            int(price),
            )

        await tg_edit(
            chat_id, message_id,
            f"✅ Жазылдыңыз! (№{booking_id})\nАдмин жақында хабарласады.\n\nҚайта меню:",
            reply_markup=main_menu_kb()
            )

        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, draft.salon_id)
        if admin_chat_id:
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
            await tg_send(admin_chat_id, admin_text)

        clear_draft(chat_id)
        return
   
    if data == "confirm:no":
        await tg_edit(chat_id, message_id, "❌ Болдырылмады. Уақытты қайта таңдаңыз:", reply_markup=times_kb())
        draft.time = None
        return

    # ----------------------------
    # FALLBACK
    # ----------------------------
    await tg_edit(chat_id, message_id, "Түсінбедім. Мәзірден таңдаңыз:", reply_markup=main_menu_kb())