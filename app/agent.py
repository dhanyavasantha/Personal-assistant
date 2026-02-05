from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import PromptTemplate
from datetime import datetime, timedelta
from langchain.tools import tool
from assistant_mcp.client import mcp_check_availability, mcp_send_notification
from app.state import agent_state
from app.calendar_reader import create_calendar_event, update_calendar_event
from rag.retriever import get_relevant_context
import asyncio

load_dotenv()

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


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

tools = [mcp_availability, mcp_notify]

prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad"],
    template=(
        "You are a personal scheduling assistant.\n"
        "You can reason step-by-step and use tools.\n\n"
        "Rules:\n"
        "- ALWAYS use tools for scheduling decisions\n"
        "- If rescheduling is required, ASK for confirmation\n"
        "- Execute actions ONLY after confirmation\n\n"
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
    verbose=True
)

def process_message(user_input: str):
    now = datetime.now()
    resolved_date = None

    if "tomorrow" in user_input.lower():
        resolved_date = (now + timedelta(days=1)).strftime("%m-%d-%Y")
    elif "today" in user_input.lower():
        resolved_date = now.strftime("%m-%d-%Y")

    if resolved_date:
        user_input += (
            f"\n\nIMPORTANT:\n"
            f"- Today's date is {now.strftime('%m-%d-%Y')}\n"
            f"- Use date: {resolved_date}\n"
        )
    result = agent_executor.invoke({"input": user_input})
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
                mcp_notify.run({"message": message})
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
        user_input += f"\n\nContext:\n{rag_context}\n"

        # ============================
        # 🧠 RUN AGENT
        # ============================
        if not agent_state.get("awaiting_confirmation"):
            result = agent_executor.invoke({"input": user_input})
            output = result["output"]
        else:
            continue
        
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

        if isinstance(output, dict) and output.get("status") == "NEEDS_CONFIRMATION":
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



