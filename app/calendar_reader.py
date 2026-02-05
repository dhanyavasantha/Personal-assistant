import os
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import pytz

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events"
]


def get_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid or not creds.has_scopes(SCOPES):
        flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",
        SCOPES
        )
        creds = flow.run_local_server(
        port=0,
        prompt="consent",
        include_granted_scopes="true"
    )

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_events_for_day(date: str):
    """
    date format: MM-DD-YYYY
    """
    service = get_calendar_service()

    start = datetime.strptime(date, "%m-%d-%Y")
    end = start + timedelta(days=1)

    tz = pytz.timezone("America/New_York")

    start = tz.localize(start)
    end = tz.localize(end)

    events = service.events().list(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute().get("items", [])

    meetings = []

    for event in events:
        start_time = event["start"].get("dateTime")
        end_time = event["end"].get("dateTime")

        if start_time and end_time:
            meetings.append({
                "event_id": event["id"],           # 🔑 REQUIRED
                "title": event.get("summary", "Meeting"),
                "start": datetime.fromisoformat(start_time).strftime("%m-%d-%Y %H:%M"),
                "end": datetime.fromisoformat(end_time).strftime("%m-%d-%Y %H:%M")
            })

    return meetings

def create_calendar_event(
    date: str,
    start_time: str,
    end_time: str,
    title: str = "Auto-booked Meeting",
    description: str = "Scheduled automatically by Personal Assistant Agent"
):
    service = get_calendar_service()

    tz = pytz.timezone("America/New_York")

    start_dt = tz.localize(
        datetime.strptime(f"{date} {start_time}", "%m-%d-%Y %H:%M")
    )
    end_dt = tz.localize(
        datetime.strptime(f"{date} {end_time}", "%m-%d-%Y %H:%M")
    )

    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "America/New_York",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "America/New_York",
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return created_event["id"]

def to_rfc3339(dt_str: str):
    """
    Converts 'MM-DD-YYYY HH:MM' → RFC3339 with timezone
    """
    tz = pytz.timezone("America/New_York")
    dt = tz.localize(
        datetime.strptime(dt_str, "%m-%d-%Y %H:%M")
    )
    return dt.isoformat()

def update_calendar_event(event_id: str, new_start: str, new_end: str):
    service = get_calendar_service()

    event = service.events().get(
        calendarId="primary",
        eventId=event_id
    ).execute()

    event["start"]["dateTime"] = to_rfc3339(new_start)
    event["end"]["dateTime"] = to_rfc3339(new_end)

    updated_event =service.events().update(
        calendarId="primary",
        eventId=event_id,
        body=event
    ).execute()

    return updated_event["id"]


