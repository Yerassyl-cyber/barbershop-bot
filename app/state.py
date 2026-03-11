from dataclasses import dataclass
from typing import Optional

@dataclass
class BookingDraft:
    salon_id: Optional[int] = None
    master_id: Optional[str] = None
    service_id: Optional[str] = None
    day: Optional[str] = None
    time: Optional[str] = None
    step: Optional[str] = None
    client_phone: Optional[str] = None
    client_name: Optional[str] = None
    main_message_id: Optional[int] = None

BOOKINGS: dict[int, BookingDraft] = {}

def get_draft(chat_id: int) -> BookingDraft:
    if chat_id not in BOOKINGS:
        BOOKINGS[chat_id] = BookingDraft()
    return BOOKINGS[chat_id]

def clear_draft(chat_id: int):
    BOOKINGS.pop(chat_id, None)

def clear_booking_fields(chat_id: int):
    d = get_draft(chat_id)
    d.master_id = None
    d.service_id = None
    d.day = None
    d.time = None
    d.step = None
    d.client_phone = None
    d.client_name = None
    d.main_message_id = None