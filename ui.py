import streamlit as st
from app.agent import process_message

st.set_page_config(page_title="Personal Assistant", layout="centered")

st.title("Personal Assistant")

st.write("Type your request below:")

user_input = st.text_input("Enter meeting request")

if st.button("Submit"):

    if user_input:
        st.write("Processing...")

        response = process_message(user_input)

        st.success("Assistant Response:")
        st.write(response)
    else:
        st.warning("Please enter something.")
