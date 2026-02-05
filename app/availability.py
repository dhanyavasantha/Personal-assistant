from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

WORK_START = os.getenv("WORK_START", "09:00")
WORK_END = os.getenv("WORK_END", "18:00")

LUNCH_START = os.getenv("LUNCH_START", "12:30")
LUNCH_END = os.getenv("LUNCH_END", "13:30")

TRAVEL_BUFFER_HOURS = int(os.getenv("TRAVEL_BUFFER_HOURS", 1))


def parse_dt(value: str) -> datetime:
    return datetime.strptime(value, "%m-%d-%Y %H:%M")


def overlaps(start1, end1, start2, end2) -> bool:
    return max(start1, start2) < min(end1, end2)


def get_travel_buffer(travel: dict) -> timedelta:
    # Fixed buffer for now, dynamic later
    return timedelta(hours=TRAVEL_BUFFER_HOURS)


def evaluate_availability(
    date: str,
    start_time: str,
    end_time: str,
    meetings: list,
    travels: list,
    urgent: bool = False
) -> dict:
    """
    Decide if a meeting can be booked autonomously.
    """

    slot_start = parse_dt(f"{date} {start_time}")
    slot_end = parse_dt(f"{date} {end_time}")

    # 1. Working hours (hard rule)
    work_start = parse_dt(f"{date} {WORK_START}")
    work_end = parse_dt(f"{date} {WORK_END}")

    if not (work_start <= slot_start and slot_end <= work_end):
        return {
            "status": "CONFLICT",
            "reasons": ["Outside working hours"],
            "action": "REJECT"
        }

    # 2. Lunch (soft rule)
    lunch_start = parse_dt(f"{date} {LUNCH_START}")
    lunch_end = parse_dt(f"{date} {LUNCH_END}")

    if overlaps(slot_start, slot_end, lunch_start, lunch_end):
        if urgent:
            pass  # allow override
        else:
            return {
                "status": "NEEDS_CONFIRMATION",
                "reasons": ["Overlaps with lunch time"],
                "action": "ASK_USER"
            }

    # 3. Existing meetings (hard rule)
    for meeting in meetings:
        m_start = parse_dt(meeting["start"])
        m_end = parse_dt(meeting["end"])

        if overlaps(slot_start, slot_end, m_start, m_end):
            conflicting_data = {
            "event_id": meeting["event_id"],
            "title": meeting.get("title", "Meeting"),
            "old_start": meeting["start"],
            "old_end": meeting["end"]
        }
            if urgent:
                return {
                    "status": "NEEDS_CONFIRMATION",
                    "reasons": [f"Conflicts with meeting: {meeting.get('title', 'Meeting')} (can be moved)"],
                    "action": "RESCHEDULE_EXISTING",
                    "conflicting_meeting": conflicting_data
               }
            else:
                return {
                    "status": "CONFLICT",
                    "reasons": ["Conflicts with existing meeting"],
                    "action": "ASK_USER",
                    "conflicting_meeting": conflicting_data
                }

    # 4. Travel + buffer (hard rule)
    for travel in travels:
        t_start = parse_dt(travel["start"])
        t_end = parse_dt(travel["end"]) + get_travel_buffer(travel)

        if overlaps(slot_start, slot_end, t_start, t_end):
            return {
                "status": "CONFLICT",
                "reasons": ["Conflicts with travel or buffer time"],
                "action": "REJECT"
            }

    # 5. Free slot
    return {
        "status": "AVAILABLE",
        "reasons": [],
        "action": "AUTO_BOOK"
    }


# Safe local test
if __name__ == "__main__":
    meetings = [
        {
            "event_id": "TEST_EVENT_ID",
            "title": "Team Sync",
            "start": "02-10-2026 10:00",
            "end": "02-10-2026 11:00"
        }
    ]

    travels = [
        {
            "start": "02-10-2026 14:00",
            "end": "02-10-2026 16:00"
        }
    ]

    print(
        evaluate_availability(
            "02-10-2026",
            "12:00",
            "13:00",
            meetings,
            travels
        )
    )
