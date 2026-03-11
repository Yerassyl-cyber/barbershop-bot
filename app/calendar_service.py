import json
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import GOOGLE_CALENDAR_ID, GOOGLE_SERVICE_ACCOUNT_JSON

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_service():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON орнатылмаған")

    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)

    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=SCOPES,
    )

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _almaty_dt(day: str, time_str: str) -> datetime:
    dt = datetime.strptime(f"{day} {time_str}", "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=timezone(timedelta(hours=5)))


def create_calendar_event(
    salon_name: str,
    master_name: str,
    service_name: str,
    client_name: str | None,
    client_phone: str | None,
    day: str,
    time_str: str,
    duration_minutes: int = 30,
) -> str:
    if not GOOGLE_CALENDAR_ID:
        raise RuntimeError("GOOGLE_CALENDAR_ID орнатылмаған")

    service = _get_service()

    start_dt = _almaty_dt(day, time_str)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event = {
        "summary": f"{service_name} — {master_name}",
        "description": (
            f"Salon: {salon_name}\n"
            f"Master: {master_name}\n"
            f"Client: {client_name or '-'}\n"
            f"Phone: {client_phone or '-'}"
        ),
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Almaty",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Almaty",
        },
    }

    created = service.events().insert(
        calendarId=GOOGLE_CALENDAR_ID,
        body=event
    ).execute()

    return created["id"]