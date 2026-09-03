import streamlit as st
import google.generativeai as genai

# Page configuration
st.set_page_config(
    page_title="MERCHX - Autonomous AI Commerce Protocol",
    page_icon="🛡️",
    layout="centered"
)

# UI Header
st.title("🛡️ MERCHX")
st.subheader("Autonomous AI Commerce Protocol")
st.caption("AI-Powered Buyer with Deterministic Policy, Inventory, and Risk Guardrails")

# Fetch API Key securely from Streamlit Secrets
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.error("API Key missing! Please configure GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

# Configure Generative AI Model
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# User Input Section
user_query = st.text_input(
    label="Product Query",
    placeholder="e.g., Wireless noise-cancelling headphones under $100",
    help="Enter what product you want the AI Buyer to discover and evaluate."
)

if st.button("Search & Evaluate Product", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a valid product requirement.")
    else:
        with st.spinner("MERCHX Protocol: Validating inventory, calculating quote, and checking policy limits..."):
            try:
                system_prompt = f"""
                You are MERCHX, an enterprise autonomous commerce protocol assistant.
                The buyer has issued the following procurement request: "{user_query}"

                Respond with a structured response including:
                1. Product Selection & Estimated Price
                2. Inventory Availability Status (Simulated)
                3. Policy Compliance Check (Max limit: $150, Category check)
                4. Cryptographic Quote Summary (Mock Quote ID: MX-QT-XXXX)
                5. Authorization Decision: APPROVED or BLOCKED with clear reasoning.
                """

                response = model.generate_content(system_prompt)
                
                st.markdown("### 📋 Protocol Execution Report")
                st.success(response.text)

            except Exception as e:
                st.error(f"Error executing agent pipeline: {str(e)}")
