from .telegram_api import tg_send, tg_edit
from .state import get_draft, clear_draft,clear_booking_fields  # немесе clear_booking_fields
import asyncio
from datetime import datetime, timedelta
from .calendar_service import create_calendar_event, delete_calendar_event
from .db import (
    get_salon_by_start_code,
    get_masters_by_salon,
    get_services_by_salon,
    insert_booking,
    is_slot_taken,
    set_booking_calendar_event_id,
    get_user_active_bookings,get_active_bookings_by_salon_and_day,
    get_booking_for_cancel,remove_closed_day,
    get_closed_days,get_booking_full_info, cancel_booking, get_salon_admin_chat_id,add_closed_day
)

async def handle_my_bookings(chat_id: int, message_id: int):
    rows = await asyncio.to_thread(get_user_active_bookings, chat_id)

    if not rows:
        await tg_edit(
            chat_id,
            message_id,
            "Сізде белсенді жазылу жоқ.",
            reply_markup=main_menu_kb()
        )
        return

    text = "📋 Менің жазылуларым:\n\n"

    for row in rows:
        booking_id = row[0]
        day = row[1]
        time_ = row[2]
        status = row[3]
        master_name = row[4] or "-"
        service_title = row[5] or "-"
        price = row[6]

        text += (
            f"№{booking_id}\n"
            f"✂️ Мастер: {master_name}\n"
            f"🛠 Қызмет: {service_title}\n"
            f"📅 Күн: {day}\n"
            f"⏰ Уақыт: {time_}\n"
            f"💳 Баға: {price} тг\n"
            f"📌 Статус: {status}\n\n"
        )

    await tg_edit(
        chat_id,
        message_id,
        text,
        reply_markup=my_bookings_kb(rows)
    )
    
def my_bookings_kb(rows):
    keyboard = []

    for row in rows:
        booking_id = row[0]
        keyboard.append([
            {
                "text": f"❌ Отменить №{booking_id}",
                "callback_data": f"cancel:{booking_id}"
            }
        ])

    keyboard.append([{"text": "⬅️ Артқа", "callback_data": "menu:back"}])

    return {"inline_keyboard": keyboard}

def client_confirm_kb():
    return {
        "inline_keyboard": [
            [{"text": "✅ Дұрыс", "callback_data": "client_ok"}],
            [{"text": "✏️ Өзгерту", "callback_data": "client_edit"}],
        ]
    }

def booking_done_kb(booking_id: int):
    return {
        "inline_keyboard": [
            [{"text": "❌ Записьті болдырмау", "callback_data": f"cancel:{booking_id}"}],
            [{"text": "🏠 Басты мәзір", "callback_data": "menu:back"}],
        ]
    }
async def handle_cancel(callback_data, chat_id, message_id):
    try:
        booking_id = int(callback_data.split(":")[1])

        row = await asyncio.to_thread(get_booking_full_info, booking_id)
        master_name = row[10]
        service_title = row[11]
        day = row[5]
        time_ = row[6]
        phone = row[10]
        name = row[11]
        if not row:
            await tg_edit(chat_id, message_id, "⚠️ Запись табылмады.")
            return
        row_user_chat_id = row[1]
        row_status = row[8]
        calendar_event_id = row[9]   # 🔥 МІНЕ ОСЫ ЖЕР ДҰРЫС БОЛУ КЕРЕК

        print("DELETE EVENT ID:", calendar_event_id)

        if int(row_user_chat_id) != int(chat_id):
            await tg_edit(chat_id, message_id, "❌ Бұл запись сізге тиесілі емес.")
            return

        if row_status == "cancelled":
            await tg_edit(chat_id, message_id, "ℹ️ Бұл запись бұрыннан отмена жасалған.")
            return

        await asyncio.to_thread(cancel_booking, booking_id)

        if calendar_event_id:
            await asyncio.to_thread(delete_calendar_event, str(calendar_event_id))
        salon_id = row[2]
        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, salon_id)

        if admin_chat_id:
          await tg_send(
              admin_chat_id,
              f"❌ Клиент отменил запись.\n\n"
              f"№{booking_id}\n"
              f"👤 {name}\n"
              f"📞 {phone}\n"
              f"✂️ {master_name}\n"
              f"🛠 {service_title}\n"
              f"📅 {day} {time_}"
              )
          await tg_send(
                chat_id,
                f"❌ Запись отменена.\n\n"
                f"✂️ Мастер: {master_name}\n"
                f"🛠 Қызмет: {service_title}\n"
                f"📅 Күн: {day}\n"
                f"⏰ Уақыт: {time_}"
                )

    except Exception as e:
        print(f"CANCEL ERROR: {e}")
        await tg_send(chat_id, f"⚠️ Отмена кезінде қате шықты: {e}")
TIMES = [
    "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
    "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30",
    "18:00", "18:30"
]


def main_menu_kb():
    return {
        "inline_keyboard": [
            [{"text": "📅 Запись", "callback_data": "menu:book"}],
            [{"text": "💰 Бағалар", "callback_data": "menu:prices"}],
            [{"text": "📋 Менің жазылуларым", "callback_data": "menu:my_bookings"}],
        ]
    }

def phone_request_kb():
    return {
        "keyboard": [
            [{"text": "📞 Телефон нөмірімді жіберу", "request_contact": True}],
            [{"text": "⬅️ Бас тарту"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

def remove_reply_kb():
    return {"remove_keyboard": True}

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

WEEKDAYS = {
    0: "Дс/Пн",
    1: "Сс/Вт",
    2: "Ср/Ср",
    3: "Бс/Чт",
    4: "Жм/Пт",
    5: "Сб/Сб",
    6: "Жс/Вс",
}
def days_kb(salon_id: int):
    rows = []
    today = datetime.now()
    closed_days = set(get_closed_days(salon_id))

    for i in range(5):
        d = today + timedelta(days=i)
        iso = d.strftime("%Y-%m-%d")

        if iso in closed_days:
            continue

        weekday_label = WEEKDAYS[d.weekday()]
        label = f"{weekday_label} {d.strftime('%d.%m')}"
        
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
def admin_menu_kb():
    return {
        "inline_keyboard": [
            [{"text": "📋 Записьтер", "callback_data": "admin_bookings_days"}],
            [{"text": "📅 Күнді жабу", "callback_data": "admin_close_day"}],
            [{"text": "📅 Күнді ашу", "callback_data": "admin_open_day"}],
        ]
    }

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
        text += f"{title}: {price} тг\n"

    await tg_edit(chat_id, message_id, text + "\n⬅️ Артқа қайтайық:", reply_markup=main_menu_kb())

async def handle_message(chat_id: int, text: str | None, message: dict):
    draft = get_draft(chat_id)
    if text == "/admin":
        if not draft.salon_id:
            await tg_send(chat_id, "Салон таңдалмаған.")
            return

        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, draft.salon_id)

        if not admin_chat_id or int(admin_chat_id) != int(chat_id):
            await tg_send(chat_id, "❌ Сіз админ емессіз.")
            return

        await tg_send(chat_id, "Админ мәзірі:", reply_markup=admin_menu_kb())
        return
    if getattr(draft, "step", None) == "admin_wait_day_close":
        day = (text or "").strip()

        try:
            datetime.strptime(day, "%Y-%m-%d")
        except:
            await tg_send(chat_id, "❌ Күн форматы қате. Мысалы: 2026-03-20")
            return

        await asyncio.to_thread(add_closed_day, draft.salon_id, day, "admin")
        draft.step = None

        await tg_send(chat_id, f"✅ Күн жабылды: {day}", reply_markup=admin_menu_kb())
        return
    
    if getattr(draft, "step", None) == "admin_wait_day_open":
        day = (text or "").strip()

        try:
            datetime.strptime(day, "%Y-%m-%d")
        except:
            await tg_send(chat_id, "❌ Күн форматы қате. Мысалы: 2026-03-20")
            return

        await asyncio.to_thread(remove_closed_day, draft.salon_id, day)
        draft.step = None

        await tg_send(chat_id, f"✅ Күн ашылды: {day}", reply_markup=admin_menu_kb())
        return
    if text == "⬅️ Бас тарту":
        draft.step = None
        await tg_send(chat_id, "Таңдаңыз:", reply_markup=remove_reply_kb())
        if draft.salon_id:
            await tg_send(chat_id, "Негізгі мәзір:", reply_markup=main_menu_kb())
        else:
             await tg_send(chat_id, "Салон таңдалмаған. /start арқылы қайта кіріңіз.")
        return
    # телефон күтіп тұрсақ
    if getattr(draft, "step", None) == "wait_phone":
        draft.client_phone = text.strip()
        draft.step = "wait_name"

        await tg_send(chat_id, "👤 Атыңызды жазыңыз:")
        return
    

    if getattr(draft, "step", None) == "wait_name":
        draft.client_name = text.strip()
        draft.step = None
        await tg_send(
            chat_id,
           f"Тексеріңіз:\n\n"
           f"👤 Аты: {draft.client_name}\n"
           f"📞 Телефон: {draft.client_phone}",
           reply_markup=client_confirm_kb()
           )
        return
    

async def handle_callback(chat_id: int, data: str, message_id: int):
    draft = get_draft(chat_id)
    if data.startswith("cancel:"):
        await handle_cancel(data, chat_id, message_id)
        return
    
    if data == "admin_close_day":
        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, draft.salon_id)
        if not admin_chat_id or int(admin_chat_id) != int(chat_id):
            await tg_edit(chat_id, message_id, "❌ Бұл бөлім тек админге.")
            return

        draft.step = "admin_wait_day_close"
        await tg_edit(chat_id, message_id, "Жабылатын күнді жазыңыз:\n\nМысалы: 2026-03-20")
        return
    if data == "admin_open_day":
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "❌ Салон таңдалмаған.")
            return

        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, draft.salon_id)
        if not admin_chat_id or int(admin_chat_id) != int(chat_id):
            await tg_edit(chat_id, message_id, "❌ Бұл бөлім тек админге.")
            return

        draft.step = "admin_wait_day_open"
        await tg_edit(
            chat_id,
            message_id,
            "Ашылатын күнді жазыңыз:\n\nМысалы: 2026-03-20"
            )
        return
    if data == "admin_bookings_days":
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "❌ Салон таңдалмаған.")
            return

        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, draft.salon_id)
        if not admin_chat_id or int(admin_chat_id) != int(chat_id):
            await tg_edit(chat_id, message_id, "❌ Бұл бөлім тек админге.")
            return

        rows = []
        today = datetime.now()

        for i in range(5):
            d = today + timedelta(days=i)
            iso = d.strftime("%Y-%m-%d")
            weekday_label = WEEKDAYS[d.weekday()]
            label = f"{weekday_label} {d.strftime('%d.%m')}"
            rows.append([{"text": label, "callback_data": f"admin_bookings_day:{iso}"}])

        rows.append([{"text": "⬅️ Артқа", "callback_data": "menu:back"}])

        await tg_edit(
            chat_id,
            message_id,
            "Қай күннің записьтерін көргіңіз келеді?",
            reply_markup={"inline_keyboard": rows}
            )
        return
    if data.startswith("admin_bookings_day:"):
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "❌ Салон таңдалмаған.")
            return

        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, draft.salon_id)
        if not admin_chat_id or int(admin_chat_id) != int(chat_id):
            await tg_edit(chat_id, message_id, "❌ Бұл бөлім тек админге.")
            return

        day = data.split(":", 1)[1]

        rows = await asyncio.to_thread(
            get_active_bookings_by_salon_and_day,
            draft.salon_id,
            day
            )

        if not rows:
            await tg_edit(
                chat_id,
                message_id,
                f"Бұл күнге запись жоқ.\n\n📅 {day}",
                reply_markup=admin_menu_kb()
                )
            return

        text = f"📋 Записьтер\n📅 {day}\n\n"
        keyboard = []

        for row in rows:
            booking_id = row[0]
            client_phone = row[2] or "-"
            client_name = row[3] or "-"
            day = row[4]
            time_ = row[5]
            master_name = row[7] or "-"
            service_title = row[8] or "-"
            price = row[9]

            text += (
                f"№{booking_id}\n"
                f"👤 Клиент: {client_name}\n"
                f"📞 Телефон: {client_phone}\n"
                f"⏰ Уақыт: {time_}\n"
                f"✂️ Мастер: {master_name}\n"
                f"🛠 Қызмет: {service_title}\n"
                f"💳 Баға: {price} тг\n"
             
                )   

            keyboard.append([
                {"text": f"❌ Отменить №{booking_id}", "callback_data": f"admin_cancel:{booking_id}"}
                ])

        keyboard.append([{"text": "⬅️ Күндерге қайту", "callback_data": "admin_bookings_days"}])

        await tg_edit(
            chat_id,
            message_id,
            text,
            reply_markup={"inline_keyboard": keyboard}
            )
        return
    if data.startswith("admin_cancel:"):
        booking_id = int(data.split(":")[1])
        row = await asyncio.to_thread(get_booking_full_info, booking_id)
        if not row:
            await tg_edit(chat_id, message_id, "⚠️ Запись табылмады.")
            return

        client_chat_id = row[1]
        row_status = row[8]
        calendar_event_id = row[9]

        if row_status == "cancelled":
            await tg_edit(chat_id, message_id, "ℹ️ Бұл запись бұрыннан отмена жасалған.")
            return

        if calendar_event_id:
            await asyncio.to_thread(delete_calendar_event, str(calendar_event_id))

        await asyncio.to_thread(cancel_booking, booking_id)

        await tg_send(
            client_chat_id,
            f"❌ Администратор сіздің жазылуыңызды болдырмады.\n\n№{booking_id}"
            )

        await tg_edit(
            chat_id,
            message_id,
            f"✅ Запись отменена. №{booking_id}"
            )
        return
    # ----------------------------
    # MAIN MENU
    # ----------------------------
    if data == "menu:prices":
        await handle_prices(chat_id, message_id)
        return
    if data == "menu:my_bookings":
        await handle_my_bookings(chat_id, message_id)
        return
    if data == "menu:book":
        if not draft.salon_id:
            await tg_edit(chat_id, message_id, "Салон таңдалмаған. /start link арқылы кіріңіз.")
            return

        # салонды сақтап, қалғанын тазалау
        clear_booking_fields(chat_id)
        draft = get_draft(chat_id)

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
        await tg_edit(chat_id, message_id, "Күнді таңдаңыз:", reply_markup=days_kb(draft.salon_id))
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
        await tg_edit(chat_id, message_id, "Күнді таңдаңыз:",reply_markup=days_kb(draft.salon_id))
        return

    # ----------------------------
    # TIME -> IMMEDIATE BOOKING (логика өзгермейді)
    # ----------------------------
# ----------------------------
# TIME -> SHOW CONFIRMATION (растау арқылы бронь)
# ----------------------------
    if data.startswith("time:"):
        try:
            t = data.split(":", 1)[1]
            draft.time = t

            if not draft.salon_id:
                await tg_edit(
                    chat_id,
                    message_id,
                    "Салон таңдалмаған. /start арқылы кіріңіз.",
                    reply_markup=main_menu_kb()
                )
                return

            if not draft.master_id:
                await tg_edit(
                    chat_id,
                    message_id,
                    "Мастер таңдалмаған. Қайтадан таңдаңыз.",
                    reply_markup=masters_kb(draft.salon_id)
                )
                return

            if not draft.service_id:
                await tg_edit(
                    chat_id,
                    message_id,
                    "Қызмет таңдалмаған. Қайтадан таңдаңыз.",
                    reply_markup=services_kb(draft.salon_id)
                )
                return

            if not draft.day:
                await tg_edit(
                    chat_id,
                    message_id,
                    "Күн таңдалмаған. Қайтадан таңдаңыз.",
                    reply_markup=days_kb(draft.salon_id)
                )
                return

            masters = await asyncio.to_thread(get_masters_by_salon, draft.salon_id)
            master_name = next(
                (name for (mid, name) in masters if str(mid) == str(draft.master_id)),
                "?"
            )

            services = await asyncio.to_thread(get_services_by_salon, draft.salon_id)
            service_row = next(
                ((sid, title, price) for (sid, title, price) in services if str(sid) == str(draft.service_id)),
                None
            )

            if not service_row:
                await tg_edit(
                    chat_id,
                    message_id,
                    "Қызмет табылмады. Қайта таңдаңыз.",
                    reply_markup=services_kb(draft.salon_id)
                )
                return

            _, service_name, price = service_row

            taken = await asyncio.to_thread(
                is_slot_taken,
                draft.salon_id,
                draft.master_id,
                draft.day,
                draft.time
            )

            if taken:
                await tg_edit(
                    chat_id,
                    message_id,
                    "⚠️ Бұл уақыт бос емес. Басқа уақыт таңдаңыз:",
                    reply_markup=times_kb()
                )
                return

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

        except Exception as e:
            print(f"TIME CALLBACK ERROR: {e}")
            await tg_send(chat_id, f"⚠️ Қате шықты: {e}")
            return

    # ----------------------------
    # CONFIRMATION (қалсын, бірақ дұрыс жұмыс істесін)
    # ЕСКЕРТУ: қазіргі логикада бұл шақырылмауы мүмкін
    # ----------------------------
    if data == "confirm:yes":
        draft.main_message_id = message_id

        if not getattr(draft, "client_phone", None):
            draft.step = "wait_phone"

            await tg_edit(
                chat_id,
                message_id,
                "📞 Телефон нөміріңізді жазыңыз:",
                reply_markup=None
                )
            return

        if not getattr(draft, "client_name", None):
            draft.step = "wait_name"

            await tg_send(
                chat_id,
                "👤 Атыңызды жазыңыз:"
                )
            return

        await tg_edit(
            chat_id,
            message_id,
           f"Тексеріңіз:\n\n"
           f"👤 Аты: {draft.client_name}\n"
           f"📞 Телефон: {draft.client_phone}",
            reply_markup=client_confirm_kb()
            )
        return
    if data == "client_edit":
        draft.client_phone = None
        draft.step = "wait_phone"

        await tg_edit(
            chat_id,
            message_id,
            "📞 Телефонды қайта жіберіңіз:",
            reply_markup=None
            )
        await tg_send(chat_id, "👇 Батырманы басыңыз:", reply_markup=phone_request_kb())
        return
    if data == "client_ok":
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
                chat_id,
                draft.salon_id,
                draft.master_id,
                draft.service_id,
                draft.day,
                draft.time,
                int(price),
                getattr(draft, "client_phone", None),
                getattr(draft, "client_name", None),
                )
        salon_name = "TN Barbershop"
        calendar_event_id = None
        try:
            calendar_event_id =await asyncio.to_thread(
                create_calendar_event,
                salon_name,
                master_name,
                service_name,
                getattr(draft, "client_name", None),
                getattr(draft, "client_phone", None),
                draft.day,
                draft.time,
                30,  # duration_minutes
            )
            if calendar_event_id:
                await asyncio.to_thread(
                    set_booking_calendar_event_id,
                    booking_id,
                    calendar_event_id
                    )
        except Exception as e:
            print(f"Google Calendar error: {e}")

        await tg_edit(
            chat_id,
            message_id,
            f"✅ Жазылдыңыз! (№{booking_id})\n\nҚажет болса төмендегі батырмамен отмена жасай аласыз:",
            reply_markup=booking_done_kb(booking_id)
            )

        admin_chat_id = await asyncio.to_thread(get_salon_admin_chat_id, draft.salon_id)
        if admin_chat_id:
            admin_text = (
               f"🆕 Жаңа запись! №{booking_id}\n\n"
               f"👤 Клиент: {getattr(draft, 'client_name', '-')}\n"
               f"📞 Тел: {getattr(draft, 'client_phone', '-')}\n"
               f"✂️ Мастер: {master_name}\n"
               f"🛠 Қызмет: {service_name}\n"
               f"📅 Күн: {draft.day}\n"
               f"⏰ Уақыт: {draft.time}\n"
               f"💳 Баға: {price} тг"
               )      
            await tg_send(
                admin_chat_id,
                admin_text,
                reply_markup={
                    "inline_keyboard": [
                        [{"text": "❌ Записьті болдырмау", "callback_data": f"admin_cancel:{booking_id}"}]
                        ]
                    }
                )

        clear_booking_fields(chat_id)
        return
    
    if data == "confirm:no":
        await tg_edit(chat_id, message_id, "❌ Болдырылмады. Уақытты қайта таңдаңыз:", reply_markup=times_kb())
        draft.time = None
        return

    # ----------------------------
    # FALLBACK
    # ----------------------------
    await tg_edit(chat_id, message_id, "Түсінбедім. Мәзірден таңдаңыз:", reply_markup=main_menu_kb())