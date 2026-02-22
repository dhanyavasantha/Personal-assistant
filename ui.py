import streamlit as st
from datetime import datetime
from app.agent import process_message
import re

# ==============================
# Helpers
# ==============================

def format_time(iso_string):
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%I:%M %p")
    except:
        return iso_string

def format_duration(duration_str):
    match = re.findall(r"\d+", duration_str)
    if len(match) == 2:
        return f"{match[0]}h {match[1]}m"
    elif len(match) == 1:
        return f"{match[0]}h"
    return duration_str


# ==============================
# Page Config
# ==============================

st.set_page_config(page_title="Personal Assistant", layout="wide")

# ==============================
# Custom CSS (YOUR ORIGINAL STYLE)
# ==============================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #f5f7fa, #e4ecf7);
}

.sticky-header {
    position: sticky;
    top: 0;
    background: linear-gradient(135deg, #f7f9fc, #e9f0fa);
    z-index: 999;
    padding-top: 10px;
}

.main-title {
    text-align: center;
    font-size: 48px;
    font-weight: 700;
    color: #1F4E79;
}

.subtitle {
    text-align: center;
    font-size: 18px;
    color: #5D6D7E;
    margin-bottom: 15px;
}

.flight-card {
    background-color: #ffffff;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e6ecf5;
    margin-bottom: 15px;
}

.price-text {
    font-size: 26px;
    font-weight: 800;
    color: #0071c2;
}

</style>
""", unsafe_allow_html=True)

# ==============================
# Header (UNCHANGED)
# ==============================

st.markdown('<div class="sticky-header">', unsafe_allow_html=True)

st.markdown('<div class="main-title">🤖 IntelliAssist</div>', unsafe_allow_html=True)

st.markdown(
'<div class="subtitle">Hi there! 👋 I’m IntelliAssist — your intelligent personal assistant for intelligent scheduling, seamless calendar management, and smart travel planning.</div>',
unsafe_allow_html=True
)

mode = st.radio(
    "Select Mode",
    ["Chat", "Book Meeting", "Search Flights"],
    horizontal=True
)

st.divider()
st.markdown('</div>', unsafe_allow_html=True)

# ==============================
# Priceline-Style Card (NO RAW HTML)
# ==============================

def display_flight_card(flight):

    departure = format_time(flight.get("departure", ""))
    arrival = format_time(flight.get("arrival", ""))
    duration = format_duration(flight.get("duration", ""))
    airline = flight.get("airline", "")
    price = flight.get("price", "")

    with st.container():

        col1, col2 = st.columns([6, 2])

        # LEFT SIDE (route + airline)
        with col1:
            st.markdown(
                f"""
                <div style="font-size:24px; font-weight:700;">
                    {departure} 
                    <span style="color:#9ca3af;">→</span> 
                    {arrival}
                </div>
                <div style="color:#6b7280; font-size:14px;">
                    {airline} • ⏱ {duration}
                </div>
                """,
                unsafe_allow_html=True
            )

        # RIGHT SIDE (price)
        with col2:
            st.markdown(
                f"""
                <div style="text-align:right; font-size:26px; font-weight:800; color:#0071c2;">
                    ${price}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            "<div style='height:1px; background:#e5e7eb; margin:8px 0 14px 0;'></div>",
            unsafe_allow_html=True
        )

        st.divider()


# ==============================
# Session State
# ==============================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ==============================
# CHAT MODE
# ==============================

if mode == "Chat":

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if isinstance(msg["content"], list):
                for flight in msg["content"]:
                    display_flight_card(flight)
            else:
                st.markdown(msg["content"])

    user_input = st.chat_input("Type your message...")

    if user_input:

        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_message(user_input)

                if isinstance(response, list):
                    for flight in response:
                        display_flight_card(flight)
                else:
                    st.markdown(response)

        st.session_state.messages.append(
            {"role": "assistant", "content": response})


# ==============================
# BOOK MEETING MODE
# ==============================

elif mode == "Book Meeting":

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        meet_date = st.date_input("Date")

    with col2:
        start_time = st.time_input("Start Time")

    with col3:
        end_time = st.time_input("End Time")

    with col4:
        urgent = st.checkbox("Important")

    if st.button("Book Meeting"):

        date_str = meet_date.strftime("%m-%d-%Y")
        start_str = start_time.strftime("%H:%M")
        end_str = end_time.strftime("%H:%M")

        prompt = f"book meeting on {date_str} from {start_str} to {end_str}"
        if urgent:
            prompt += " urgent"

        with st.spinner("Booking..."):
            response = process_message(prompt)

        st.success(response)


# ==============================
# SEARCH FLIGHTS MODE
# ==============================

elif mode == "Search Flights":

    col1, col2, col3 = st.columns(3)

    with col1:
        from_city = st.text_input("From")

    with col2:
        to_city = st.text_input("To")

    with col3:
        travel_date = st.date_input("Travel Date")

    if st.button("Search Flights"):

        date_str = travel_date.strftime("%m-%d-%Y")
        prompt = f"search flights from {from_city} to {to_city} on {date_str}"

        with st.spinner("Searching..."):
            response = process_message(prompt)

        if isinstance(response, list):
            for flight in response:
                display_flight_card(flight)
        else:
            st.markdown(response)












