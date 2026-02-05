import os
from langchain.tools import tool
from app.availability import evaluate_availability
from app.calendar_reader import get_events_for_day, create_calendar_event
from datetime import datetime, timedelta
from app.state import agent_state
from twilio.rest import Client

def normalize_time(t: str) -> str:
    t = t.strip().upper()
    if "AM" in t or "PM" in t:
        return datetime.strptime(t, "%I:%M %p").strftime("%H:%M")
    return t

#scheduling tool
@tool
def check_availability_tool(
    date: str,
    start_time: str,
    end_time: str,
    urgent: bool = False
) -> dict:
    """
    Check availability, prepare rescheduling if needed,
    and book meetings when allowed.
    """

    # 🔒 Normalize date
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        parsed_date = datetime.strptime(date, "%m-%d-%Y")

    date = parsed_date.strftime("%m-%d-%Y")
    start_time = normalize_time(start_time)
    end_time = normalize_time(end_time)

    # 1️⃣ Calendar data
    meetings = get_events_for_day(date)

    travels = [
        {"start": f"{date} 14:00", "end": f"{date} 16:00"}
    ]

    # 2️⃣ Availability decision
    decision = evaluate_availability(
        date=date,
        start_time=start_time,
        end_time=end_time,
        meetings=meetings,
        travels=travels,
        urgent=urgent
    )

    # 🟡 CASE 1: Needs confirmation to reschedule
    if decision["action"] == "RESCHEDULE_EXISTING":
        conflicting = decision["conflicting_meeting"]
        old = conflicting

        urgent_end_dt = datetime.strptime(
            f"{date} {end_time}", "%m-%d-%Y %H:%M"
        )

        old_start_dt = datetime.strptime(old["old_start"], "%m-%d-%Y %H:%M")
        old_end_dt = datetime.strptime(old["old_end"], "%m-%d-%Y %H:%M")
        duration = old_end_dt - old_start_dt
        new_start_dt = urgent_end_dt + timedelta(minutes=30)
        new_end_dt = new_start_dt + duration

        agent_state.clear()
        agent_state["awaiting_confirmation"] = True
        agent_state["conflicting_meeting"] = conflicting
        agent_state["new_meeting"] = {
            "date": date,
            "start_time": start_time,
            "end_time": end_time
        }
        agent_state["rescheduled_meeting"] = {
            "title": old.get("title", "Meeting"),
            "old_start": old["old_start"],
            "old_end": old["old_end"],
            "new_start": new_start_dt.strftime("%m-%d-%Y %H:%M"),
            "new_end": new_end_dt.strftime("%m-%d-%Y %H:%M")
        }
        agent_state["urgent"] = urgent

        return {
            "status": "NEEDS_CONFIRMATION",
            "action": "RESCHEDULE_EXISTING",
            "conflicting_meeting": conflicting,
            "new_meeting": {
                "date": date,
                "start_time": start_time,
                "end_time": end_time
            },
            "message": (
                f"Conflicting meeting '{conflicting['title']}' "
                f"from {conflicting['old_start']}–{conflicting['old_end']} "
                f"can be moved."
            ),
            "reschedule_proposal": {
                "title": old.get("title", "Meeting"),
                "old_start": old["old_start"],
                "old_end": old["old_end"],
                "new_start": new_start_dt.strftime("%m-%d-%Y %H:%M"),
                "new_end": new_end_dt.strftime("%m-%d-%Y %H:%M")
            },
            "urgent": urgent
        }

    # 🟢 CASE 2: Slot free → book immediately
    if decision["status"] == "AVAILABLE":
        event_id = create_calendar_event(date, start_time, end_time)

        return {
            "status": "BOOKED",
            "event_id": event_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "notify": urgent,
            "notification_message": (
                f"🚨 Urgent meeting booked: {date} {start_time}–{end_time}"
                if urgent else None
            )
        }

    # 🔴 CASE 3: Hard conflict
    return decision


# =========================
# 🔹 NOTIFICATION TOOL
# =========================

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.getenv("TWILIO_FROM_NUMBER")
TWILIO_TO = os.getenv("TWILIO_TO_NUMBER")

client = Client(TWILIO_SID, TWILIO_TOKEN)

def send_notification(message: str):
    if not TWILIO_TO:
        print("⚠ TWILIO_TO_NUMBER missing")
        return
    
    client.messages.create(
        body=message,
        from_=TWILIO_FROM,
        to=TWILIO_TO
    )

@tool
def send_notification_tool(message: str) -> str:
    """
    Send an SMS notification to the user.
    """
    send_notification(message)
    return "Notification sent"
