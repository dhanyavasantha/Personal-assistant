from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import PromptTemplate
from datetime import datetime, timedelta
from langchain.tools import tool
from assistant_mcp.client import (
    mcp_check_availability,
    mcp_send_notification,
    mcp_search_flights,
    mcp_show_calendar,
    mcp_web_search
)
from app.state import agent_state
from app.tools import cancel_meeting_tool
from app.calendar_reader import get_events_for_day, create_calendar_event, update_calendar_event
from rag.retriever import get_relevant_context
import asyncio
import re
from dateutil import parser
import json

load_dotenv()

chat_history = []

# =============================
# TOOLS (UNCHANGED DESCRIPTIONS)
# =============================

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
        parsed = datetime.strptime(date, "%m-%d-%Y")
        amadeus_date = parsed.strftime("%Y-%m-%d")
    except:
        amadeus_date = date
    tool_result = asyncio.run(
        mcp_search_flights(origin, destination, amadeus_date)
    )

    # 🔥 Extract JSON string from MCP wrapper
    if hasattr(tool_result, "content") and tool_result.content:
        return tool_result.content[0].text

    return str(tool_result)


@tool
def show_calendar(date: str):
    """
    Show all calendar events for a given date.
    Use this when the user asks to see their schedule or calendar.
    Date format: MM-DD-YYYY
    """
    return asyncio.run(mcp_show_calendar(date))


@tool
def web_search(query: str):
    """
    Search the internet for real-time or up-to-date information.

    Use this tool when:
    - The user asks about current events
    - The user asks about news
    - The user asks about policies, airline rules, visa rules
    - The user asks about factual information not stored locally
    - The user asks about weather or recent updates

    Always provide a complete natural language query.
    """
    return asyncio.run(mcp_web_search(query))


# =============================
# LLM + AGENT
# =============================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

tools = [
    mcp_availability,
    mcp_notify,
    flight_search_tool,
    show_calendar,
    cancel_meeting_tool,
    web_search
]

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
        "- Execute actions ONLY after confirmation\n"
        "- If user asks about flights or travel options, use flight_search_tool\n"
        "- If the flight search tool returns structured data, return it exactly as-is without formatting\n"
        "- If user asks about schedule or calendar, use show_calendar\n"
        "- If user asks to cancel or delete a meeting, use cancel_meeting_tool\n\n"
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


# =============================
# DATE HELPERS (UNCHANGED)
# =============================

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


# =============================
# PROCESS MESSAGE
# =============================

def process_message(user_input: str):

    now = datetime.now()
    resolved_date = None
    lower = user_input.lower()

    # Date resolution
    if "tomorrow" in lower:
        resolved_date = (now + timedelta(days=1)).strftime("%m-%d-%Y")
    elif "today" in lower:
        resolved_date = now.strftime("%m-%d-%Y")

    if not resolved_date:
        weekday_date = resolve_weekday(lower)
        if weekday_date:
            resolved_date = weekday_date

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

    # 🔥 Retrieval-first (minimal safe addition)
    rag_context = get_relevant_context(user_input)

    analysis_prompt = f"""
User query:
{user_input}

Relevant internal knowledge:
{rag_context}

Extract constraints or relevant considerations.
If none, say: No special constraints.
"""

    analysis_response = llm.invoke(analysis_prompt)
    analysis_text = (
        analysis_response.content
        if hasattr(analysis_response, "content")
        else str(analysis_response)
    )

    enriched_input = f"""
User query:
{user_input}

Important considerations:
{analysis_text}

Follow these when choosing tools.
"""

    result = agent_executor.invoke({
        "input": enriched_input,
        "chat_history": chat_history
    })

    # 🔥 Intercept raw tool output BEFORE LLM formats it
    steps = result.get("intermediate_steps", [])

    if steps:
        last_action, last_observation = steps[-1]

        # If last tool called was flight_search_tool
        if last_action.tool == "flight_search_tool":
            try:
                return json.loads(last_observation)
            except:
                pass


    output = result["output"]

    # Preserve structured JSON for UI
    try:
        parsed = json.loads(output)
        if isinstance(parsed, list):
            return parsed
    except:
        pass

    chat_history.append(f"User: {user_input}")
    chat_history.append(f"Assistant: {output}")

    return output


# =============================
# RUN AGENT
# =============================

def run_agent():
    print("Scheduling assistant ready. Type 'exit' to stop.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            break

        response = process_message(user_input)

        if isinstance(response, list):
            print("\nAssistant returned structured flight data.\n")
            print(response)
        else:
            print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    run_agent()


