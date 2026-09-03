import streamlit as st
import google.generativeai as genai

st.title("🛡️ MERCHX - AI Buyer")
st.write("Hello! Naan unga MERCHX shopping agent. Enna vaanganum nu sollunga!")

# Streamlit secrets-la irundhu API key edukkudhu
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

# Model setup
model = genai.GenerativeModel('gemini-1.5-flash')

# User input
user_prompt = st.text_input("Enna search pannanum?")

if st.button("Search") and user_prompt:
    with st.spinner("MERCHX policy and stock check pannudhu..."):
        # Simple AI prompt for MERCHX feel
        system_prompt = "You are MERCHX, an AI-Native Commerce Agent. User wants to buy: " + user_prompt
        response = model.generate_content(system_prompt)
        st.success(response.text)
      
