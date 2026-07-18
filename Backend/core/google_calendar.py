import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta


# ----------------------------
# Credentials
# ----------------------------

def build_google_credentials(token: dict):
    if not token:
        raise ValueError("Google credentials token is required")

    print("TOKEN DATA:", token)
    print("TOKEN KEYS:", token.keys())
    creds = Credentials(
        token=token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
    )

    print("CREDS TOKEN:", creds.token)
    print("CREDS REFRESH:", creds.refresh_token)
    print("CLIENT ID:", creds.client_id)
    print("TOKEN URI:", creds.token_uri)
    print("VALID?", creds.valid)
    print("EXPIRED?", creds.expired)

    return creds
    
def get_calendar_service(token: dict):
    creds = build_google_credentials(token)
    return build("calendar", "v3", credentials=creds)


# ----------------------------
# Time helpers
# ----------------------------

def calculate_end_time(start_time: str, duration_minutes: int = 30):
    start_dt = datetime.fromisoformat(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return end_dt.isoformat()


# ----------------------------
# Create Event
# ----------------------------

def create_event(
    service,
    summary,
    start_time,
    end_time,
    description="",
    attendee_email: str | None = None
):
    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_time,
            "timeZone": "Africa/Cairo"
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "Africa/Cairo"
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 60},
                {"method": "popup", "minutes": 10}
            ]
        }
    }
    print("CREATING GOOGLE EVENT")

    # 🔥 FIX: attendees must be list of emails, not looped incorrectly
    if attendee_email:
        event["attendees"] = [{"email": attendee_email}]

    created_event = service.events().insert(
        calendarId=os.getenv("GOOGLE_CALENDAR_ID", "primary"),
        body=event,
        sendUpdates="all"
    ).execute()

    return created_event["id"]


# ----------------------------
# Update Event
# ----------------------------

def update_event(service, event_id, start_time, duration=30):
    end_time = calculate_end_time(start_time, duration)

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    try:
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
    except Exception as e:
        raise ValueError(f"Event not found in Google Calendar: {event_id}") from e

    event["start"]["dateTime"] = start_time
    event["end"]["dateTime"] = end_time

    # ensure reminders always exist
    event["reminders"] = {
        "useDefault": False,
        "overrides": [
            {"method": "email", "minutes": 60},
            {"method": "popup", "minutes": 10}
        ]
    }

    updated_event = service.events().update(
        calendarId=calendar_id,
        eventId=event_id,
        body=event,
        sendUpdates="all"
    ).execute()

    return updated_event


# ----------------------------
# Delete Event
# ----------------------------

def delete_event(service, event_id):
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
    except Exception:
        # 🔥 safe delete (idempotent behavior)
        # event may already be deleted externally
        pass