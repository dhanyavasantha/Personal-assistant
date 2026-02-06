import os
from langchain.tools import tool
from app.availability import evaluate_availability
from app.calendar_reader import get_events_for_day, create_calendar_event, update_calendar_event
from datetime import datetime, timedelta
from app.state import agent_state
import resend
from amadeus import Client as AmadeusClient, ResponseError

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
import resend
resend.api_key = os.getenv("RESEND_API_KEY")

@tool
def send_notification_tool(message: str) -> str:
    """Send an email notification to the user."""
    try:
        print("Sending email via Resend...")

        resend.Emails.send({
            "from": os.getenv("RESEND_FROM_EMAIL"),
            "to": [os.getenv("RESEND_TO_EMAIL")],
            "subject": "Assistant Notification",
            "html": f"<p>{message}</p>"
        })

        return "Notification email sent"

    except Exception as e:
        print("RESEND ERROR:", e)
        return f"Notification failed: {str(e)}"

    

# =========================
# ✈ FLIGHT SEARCH TOOL
# =========================

AMADEUS_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_SECRET = os.getenv("AMADEUS_API_SECRET")

amadeus = AmadeusClient(
    client_id=AMADEUS_KEY,
    client_secret=AMADEUS_SECRET
)

@tool
def search_flights_tool(origin: str, destination: str, date: str) -> str:
    """
    Search flight options between two cities or airports.
    Example origin: NYC
    Example destination: IAD
    Date format: YYYY-MM-DD
    """

    try:
        origin_code = origin.strip().upper()
        dest_code = destination.strip().upper()
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin_code,
            destinationLocationCode=dest_code,
            departureDate=date,
            adults=1,
            max=5
        )

        flights = response.data

        if not flights:
            return "No flights found."

        results = []

        for f in flights:
            airline = f["validatingAirlineCodes"][0]
            price = f["price"]["total"]

            dep = f["itineraries"][0]["segments"][0]["departure"]["at"]
            arr = f["itineraries"][0]["segments"][-1]["arrival"]["at"]

            duration = f["itineraries"][0]["duration"]

            results.append(
                f"{airline} | {dep} → {arr} | Duration: {duration} | ${price}"
            )

        return "\n".join(results)

    except ResponseError as error:
        return f"Flight search failed: {error}"