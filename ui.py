import streamlit as st
from datetime import datetime
from app.agent import process_message

st.set_page_config(page_title="Personal Assistant", layout="wide")

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- TITLE ----------
st.title("🤖 Personal Assistant")

# ---------- MODE SELECT ----------
mode = st.radio(
    "Select Mode",
    ["Chat", "Book Meeting", "Search Flights"],
    horizontal=True,
    key="mode_radio"
)

st.divider()

# ======================================================
# CHAT MODE
# ======================================================
if mode == "Chat":

    # CHAT HISTORY
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # CHAT INPUT (BOTTOM FIXED)
    user_input = st.chat_input("Type your message...")

    if user_input:
        # show user msg
        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        # assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_message(user_input)
                st.markdown(response)

        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )

# ======================================================
# BOOK MEETING MODE
# ======================================================
elif mode == "Book Meeting":

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        meet_date = st.date_input("Date", key="meet_date")

    with col2:
        start_time = st.time_input("Start Time", key="meet_start")

    with col3:
        end_time = st.time_input("End Time", key="meet_end")

    with col4:
        urgent = st.checkbox("Urgent", key="meet_urgent")

    if st.button("Book Meeting", key="meet_btn"):

        date_str = meet_date.strftime("%m-%d-%Y")
        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")

        prompt = f"book meeting on {date_str} from {start_str} to {end_str}"
        if urgent:
            prompt += " urgent"

        with st.spinner("Booking..."):
            response = process_message(prompt)

        st.success(response)

# ======================================================
# FLIGHT SEARCH MODE
# ======================================================
elif mode == "Search Flights":

    col1, col2, col3 = st.columns(3)

    with col1:
        from_city = st.text_input("From", key="flight_from")

    with col2:
        to_city = st.text_input("To", key="flight_to")

    with col3:
        travel_date = st.date_input("Travel Date", key="flight_date")

    if st.button("Search Flights", key="flight_btn"):

        date_str = travel_date.strftime("%Y-%m-%d")

        prompt = f"search flights from {from_city} to {to_city} on {date_str}"

        with st.spinner("Searching..."):
            response = process_message(prompt)

        st.success(response)


