from dataclasses import dataclass

@dataclass
@dataclass
class BookingDraft:
    salon_id: int | None = None   
    master_id: str | None = None
    service_id: str | None = None
    day: str | None = None
    time: str | None = None

# chat_id -> BookingDraft
BOOKINGS: dict[int, BookingDraft] = {}

def get_draft(chat_id: int) -> BookingDraft:
    if chat_id not in BOOKINGS:
        BOOKINGS[chat_id] = BookingDraft()
    return BOOKINGS[chat_id]

def clear_draft(chat_id: int):
    BOOKINGS.pop(chat_id, None)
