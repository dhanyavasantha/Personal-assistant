import streamlit as st
from app.agent import process_message

st.set_page_config(page_title="Personal Assistant")
st.title("AI Personal Assistant")

mode = st.radio(
    "What do you want to do?",
    ["Chat", "Schedule Meeting", "Search Flights"]
)

# ---------------- CHAT ----------------
if mode == "Chat":
    text = st.text_input("Ask anything")
    if st.button("Send"):
        response = process_message(text)
        st.success(response)

# ---------------- MEETING ----------------
elif mode == "Schedule Meeting":
    date = st.date_input("Date")
    start = st.time_input("Start Time")
    end = st.time_input("End Time")
    urgent = st.checkbox("Urgent")

    if st.button("Book Meeting"):
        start_str = start.strftime("%H:%M")
        end_str = end.strftime("%H:%M")

        msg = f"book meeting on {date} from {start_str} to {end_str}"
        if urgent:
            msg += " urgent"
        response = process_message(msg)
        st.success(response)

# ---------------- FLIGHTS ----------------
elif mode == "Search Flights":
    from_city = st.text_input("From")
    to_city = st.text_input("To")
    date = st.date_input("Travel Date")

    if st.button("Search Flights"):
        msg = f"find flights from {from_city} to {to_city} on {date}"
        response = process_message(msg)
        st.success(response)

