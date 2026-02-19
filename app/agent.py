from unittest import result
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import PromptTemplate
from datetime import datetime, timedelta
from langchain.tools import tool
from assistant_mcp.client import mcp_check_availability, mcp_send_notification, mcp_search_flights, mcp_show_calendar
from app.state import agent_state
from app.tools import cancel_meeting_tool
from app.calendar_reader import get_events_for_day, create_calendar_event, update_calendar_event
from rag.retriever import get_relevant_context
import asyncio
import re
from dateutil import parser


load_dotenv()

chat_history = []

@tool
def mcp_availability(date: str, start_time: str, end_time: str, urgent: bool=False):
    """
    Check meeting availability via MCP server and book if possible.
    """
    return asyncio.run(mcp_check_availability(date, start_time, end_time, urgent))

@tool
def mcp_notify(message: str):
    """
    Send a notification to the user via MCP server.
    """
    return asyncio.run(mcp_send_notification(message))

@tool
def flight_search_tool(origin: str, destination: str, date: str):
    """
    Search available flights between two cities on a given date.
    Always provide origin city, destination city, and date.
    Converts MM-DD-YYYY → YYYY-MM-DD for Amadeus.
    """
    try:
        # convert to Amadeus format
        parsed = datetime.strptime(date, "%m-%d-%Y")
        amadeus_date = parsed.strftime("%Y-%m-%d")
    except:
        amadeus_date = date  # fallback
    return asyncio.run(mcp_search_flights(origin, destination, amadeus_date))

@tool
def show_calendar(date: str):
    """
    Show all calendar events for a given date.
    Use this when the user asks to see their schedule or calendar.
    Date format: MM-DD-YYYY
    """
    return asyncio.run(mcp_show_calendar(date))


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

tools = [mcp_availability, mcp_notify, flight_search_tool, show_calendar, cancel_meeting_tool]

prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "chat_history"],
    template=(
        "You are a personal scheduling assistant.\n"
        "Conversation so far:\n"
        "{chat_history}\n\n"
        "You can reason step-by-step and use tools.\n\n"
        "Rules:\n"
        "- ALWAYS use tools for scheduling decisions\n"
        "- If rescheduling is required, ASK for confirmation\n"
        "- Execute actions ONLY after confirmation\n\n"
        "- If user asks about flights or travel options, use search_flights_tool\n"
        "- If the flight search tool returns structured data, return it exactly as-is without formatting\n"
        "- If user asks about schedule or calendar, use show_calendar\n"
        "- If user asks to cancel or delete a meeting, use cancel_meeting_tool\n"
        "{input}\n\n"
        "{agent_scratchpad}"
    )
)

agent = create_tool_calling_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    return_intermediate_steps=True
)

def resolve_natural_date(text: str):
    try:
        parsed = parser.parse(text, fuzzy=True)
        return parsed.strftime("%m-%d-%Y")
    except:
        return None
    
def resolve_weekday(text: str):
    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    today = datetime.now()

    for name, num in weekdays.items():
        if name in text:
            delta = (num - today.weekday() + 7) % 7
            if "next" in text or delta == 0:
                delta += 7
            target = today + timedelta(days=delta)
            return target.strftime("%m-%d-%Y")

    return None


def process_message(user_input: str):
    now = datetime.now()
    resolved_date = None
    lower = user_input.lower()
    # ✈ Handle flight requests directly via MCP (structured)
    if "flight" in user_input.lower() or "travel" in user_input.lower():
        
        import re
        
        match = re.search(
            r"from\s+([A-Za-z]{3})\s+to\s+([A-Za-z]{3})",
            user_input
        )
        
        if match:
            origin = match.group(1).upper()
            destination = match.group(2).upper()
            
            # resolve date normally using your existing logic
            date = resolved_date if resolved_date else now.strftime("%m-%d-%Y")
            
            tool_result = asyncio.run(
                mcp_search_flights(origin, destination, date)
            )

            # 🔓 Extract JSON from MCP wrapper
            if hasattr(tool_result, "content") and tool_result.content:
                raw_text = tool_result.content[0].text

                import json
                try:
                    return json.loads(raw_text)
                except Exception:
                    # If not valid JSON, just return raw text
                    return raw_text

            return tool_result


    # ---------- TODAY / TOMORROW ----------
    if "tomorrow" in lower:
        resolved_date = (now + timedelta(days=1)).strftime("%m-%d-%Y")

    elif "today" in lower:
        resolved_date = now.strftime("%m-%d-%Y")

    # ---------- WEEKDAYS ----------
    if not resolved_date:
        weekday_date = resolve_weekday(lower)
        if weekday_date:
            resolved_date = weekday_date

        # ---------- NATURAL LANGUAGE ----------
    if not resolved_date:
        match = re.search(
            r"\bon\s([a-z0-9 ,\-]+?)(?:\sfrom|\sto|\sat|$)",
            lower
       )
        if match:
            natural = match.group(1).strip()
            parsed = resolve_natural_date(natural)
            if parsed:
                resolved_date = parsed

    if resolved_date:
        user_input += (
            f"\n\nIMPORTANT:\n"
            f"- Today's date is {now.strftime('%m-%d-%Y')}\n"
            f"- Always use MM-DD-YYYY format.\n"
            f"- Use date: {resolved_date}\n"
        )
    result = agent_executor.invoke({"input": user_input, "chat_history": chat_history})
    output = result["output"]

    # 🔥 Try parsing JSON from agent output (for flights)
    import json

    try:
        parsed = json.loads(output)
        if isinstance(parsed, list):
            return parsed
    except:
        pass
    chat_history.append(f"User: {user_input}")
    chat_history.append(f"Assistant: {result['output']}")
    return result["output"]

def run_agent():
    print("Scheduling assistant ready. Type 'exit' to stop.\n")
    last_date = None
    last_start = None
    last_end = None

    while True:
        user_input = input("You: ").strip()
        user_lower = user_input.lower()
        urgent_flag = any(word in user_lower for word in ["urgent", "asap", "immediately"])

        if user_input.lower() == "exit":
            break

        # ============================
        # 🔁 CONFIRMATION EXECUTION
        # ============================
        if agent_state.get("awaiting_confirmation"):

            if user_input.lower() in ["yes", "y", "ok", "do it", "proceed"]:

                new_meeting = agent_state["new_meeting"]
                moved = agent_state.get("rescheduled_meeting")
                conflicting = agent_state.get("conflicting_meeting")

                # 1️⃣ MOVE EXISTING MEETING (REAL EXECUTION)
                if conflicting and moved:
                    update_calendar_event(
                        event_id=conflicting["event_id"],
                        new_start=moved["new_start"],
                        new_end=moved["new_end"]
                    )

                # 2️⃣ BOOK URGENT MEETING
                create_calendar_event(
                    date=new_meeting["date"],
                    start_time=new_meeting["start_time"],
                    end_time=new_meeting["end_time"]
                )

                # 3️⃣ USER MESSAGE
                message = (
                    f"✅ Done.\n"
                    f"• Urgent meeting: {new_meeting['date']} "
                    f"{new_meeting['start_time']}–{new_meeting['end_time']}\n"
                )

                if moved:
                    old_date, old_start_time = moved["old_start"].split(" ")
                    _, old_end_time = moved["old_end"].split(" ")

                    new_date, new_start_time = moved["new_start"].split(" ")
                    _, new_end_time = moved["new_end"].split(" ")

                    message += (
                        f"• Moved '{moved['title']}'\n"
                        f"  from {old_date} {old_start_time}–{old_end_time}\n"
                        f"  to   {new_date} {new_start_time}–{new_end_time}"
                    )

                # 4️⃣ NOTIFY
                mcp_send_notification(message)
                print(f"\nAssistant: {message}\n")

                agent_state.clear()
                continue

            else:
                print(
                    "\nAssistant: Okay, I won’t proceed. "
                    "Let me know what you'd like to change.\n"
                )
                agent_state.clear()
                continue

        # ============================
        # ⏱ SYSTEM TIME GROUNDING
        # ============================
        now = datetime.now()
        resolved_date = None
        
        if "tomorrow" in user_input.lower():
            resolved_date = (now + timedelta(days=1)).strftime("%m-%d-%Y")
        elif "today" in user_input.lower():
            resolved_date = now.strftime("%m-%d-%Y")
        elif any(t in user_input.lower() for t in ["am", "pm", ":"]):
            if last_date:
                resolved_date = last_date
            else:
                resolved_date = now.strftime("%m-%d-%Y")

        if resolved_date:
            last_date = resolved_date
            user_input += (
                f"\n\nIMPORTANT:\n"
                f"- Today's date is {now.strftime('%m-%d-%Y')}\n"
                f"- Use date: {resolved_date}\n"
                f"- Urgent flag is {urgent_flag}. Use this value when calling tools."
            )
        elif last_date:
            user_input += (
                f"\n\nIMPORTANT:\n"
                f"- Continue using date {last_date}\n"
                f"- Urgent flag is {urgent_flag}. Use this value when calling tools."
            )

        # ============================
        # 📚 RAG CONTEXT
        # ============================
        rag_context = get_relevant_context(user_input)
        user_input += (
            "\n\nBackground knowledge (policies, preferences, patterns):\n"
            f"{rag_context}\n"
            "Use this context when making decisions."
        )
        # ============================
        # 🧠 RUN AGENT
        # ============================
        if not agent_state.get("awaiting_confirmation"):
            result = agent_executor.invoke({"input": user_input})
            output = result["output"]
        if isinstance(output, dict):
            output = str(output)
        
        try:
            steps = result.get("intermediate_steps", [])
            if steps:
                tool_data = steps[-1][1].data
                last_start = tool_data.get("start_time")
                last_end = tool_data.get("end_time")
        except:
            pass
        

        if resolved_date:
            last_date = resolved_date

        if isinstance(output, dict) and output.get("action") in ["ASK_USER", "RESCHEDULE_EXISTING"]:
            agent_state["awaiting_confirmation"] = True
            agent_state["new_meeting"] = {
                "date": last_date,
                "start_time": last_start,
                "end_time": last_end
            }

            print("\nAssistant: I found a conflicting meeting.")
            print("I can move the existing meeting and book the new one.")
            print("Do you want me to proceed? (yes/no)\n")

        else:
            print(f"\nAssistant: {output}\n")


if __name__ == "__main__":
    run_agent()



