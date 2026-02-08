import streamlit as st
from datetime import datetime
from app.agent import process_message

st.set_page_config(page_title="Personal Assistant", layout="wide")

# ---------- CUSTOM CSS ----------
st.markdown("""
<style>

/* ---------- PAGE BACKGROUND ---------- */
.stApp {
    background: linear-gradient(135deg, #f5f7fa, #e4ecf7);
}

/* STICKY HEADER */
.sticky-header {
    position: sticky;
    top: 0;
    background: linear-gradient(135deg, #f7f9fc, #e9f0fa);
    z-index: 999;
    padding-top: 10px;
}

/* ---------- TITLE ---------- */
.main-title {
    text-align: center;
    font-size: 48px;
    font-weight: 700;
    color: #1F4E79;
}

/* ---------- SUBTITLE ---------- */
.subtitle {
    text-align: center;
    font-size: 18px;
    color: #5D6D7E;
    margin-bottom: 15px;
}

/* ---------- RADIO BUTTON STYLE ---------- */
div[role="radiogroup"] > label {
    background-color: #ffffff;
    padding: 8px 16px;
    border-radius: 20px;
    border: 1px solid #d0d7e2;
    margin-right: 10px;
    transition: 0.3s;
}

div[role="radiogroup"] > label:hover {
    background-color: #d6e4ff;
    border-color: #2E86C1;
}


/* ---------- CHAT INPUT ---------- */
.stTextInput > div > div > input {
    border-radius: 20px;
    padding: 12px;
    border: 1px solid #bfc9d9;
}

/* ---------- RESPONSE BOX ---------- */
.response-box {
    background-color: #E8F6F3;
    padding: 15px;
    border-radius: 15px;
    border-left: 5px solid #1ABC9C;
    margin-top: 15px;
}

</style>
""", unsafe_allow_html=True)


# ---------- STICKY HEADER ----------
st.markdown('<div class="sticky-header">', unsafe_allow_html=True)

st.markdown('<div class="main-title">🤖 IntelliAssist</div>', unsafe_allow_html=True)

st.markdown(
'<div class="subtitle">Hi there! 👋 I’m IntelliAssist — your intelligent personal assistant for intelligent scheduling, seamless calendar management, and smart travel planning.</div>',
unsafe_allow_html=True
)

mode = st.radio(
    "Select Mode",
    ["Chat", "Book Meeting", "Search Flights"],
    horizontal=True,
    key="mode_radio"
)

st.divider()
st.markdown('</div>', unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

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
        urgent = st.checkbox("Important", key="meet_urgent")

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

        date_str = travel_date.strftime("%m-%d-%Y")

        prompt = f"search flights from {from_city} to {to_city} on {date_str}"

        with st.spinner("Searching..."):
            response = process_message(prompt)

        st.success(response)


