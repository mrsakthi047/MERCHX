import streamlit as st
from agent_engine import detect_intent, requires_product, get_agent_response
from agent_context import AgentMemory, plan_next_step, extract_budget, extract_quantity


# ----------------------------------------------------------------
# MOCK PRODUCT CATALOG
# Replace this with a real DB / API call later.
# Keys must match KNOWN_PRODUCT_KEYWORDS in agent_context.py
# ----------------------------------------------------------------

MOCK_CATALOG = {
    "headphones": [
        {"id": "P001", "name": "Wireless ANC Headphones", "price": 7499, "stock": 20, "vendor": "SoundCo"},
        {"id": "P002", "name": "Bass Boost Headphones", "price": 5999, "stock": 12, "vendor": "AudioMax"},
        {"id": "P003", "name": "Premium Studio Headphones", "price": 8999, "stock": 5, "vendor": "SoundCo"},
    ],
    "earbuds": [
        {"id": "P004", "name": "TWS Earbuds Pro", "price": 3499, "stock": 30, "vendor": "AudioMax"},
        {"id": "P005", "name": "ANC Earbuds Mini", "price": 4999, "stock": 8, "vendor": "SoundCo"},
    ],
    "laptop": [
        {"id": "P006", "name": "Budget Laptop 14\"", "price": 32999, "stock": 4, "vendor": "TechHub"},
        {"id": "P007", "name": "Business Laptop Pro", "price": 65999, "stock": 2, "vendor": "TechHub"},
    ],
    "smartwatch": [
        {"id": "P008", "name": "Fitness Smartwatch", "price": 2999, "stock": 25, "vendor": "WearTech"},
        {"id": "P009", "name": "AMOLED Smartwatch", "price": 6499, "stock": 10, "vendor": "WearTech"},
    ],
    "mouse": [
        {"id": "P010", "name": "Wireless Mouse", "price": 799, "stock": 50, "vendor": "TechHub"},
    ],
    "keyboard": [
        {"id": "P011", "name": "Mechanical Keyboard", "price": 2499, "stock": 15, "vendor": "TechHub"},
    ],
}


def search_products(keyword, budget=None):
    """
    Searches the mock catalog for a keyword.
    Filters by budget if provided.
    Returns a list of product dicts, cheapest first.
    """
    results = MOCK_CATALOG.get(keyword, [])

    if budget:
        filtered = [p for p in results if p["price"] <= budget]
        results = filtered if filtered else results  # fall back if nothing fits

    return sorted(results, key=lambda p: p["price"])


def format_results(results):
    if not results:
        return "No matching products found."

    lines = ["Here's what I found:\n"]
    for p in results:
        lines.append(f"- **{p['name']}** — ₹{p['price']} ({p['stock']} in stock, sold by {p['vendor']})")
    return "\n".join(lines)


# ----------------------------------------------------------------
# MOCK PIPELINE (policy / risk / approval / payment simulation)
# Replace each step with real MERCHX modules as they get built.
# ----------------------------------------------------------------

POLICY_TRANSACTION_LIMIT = 10000
POLICY_ALLOWED_CATEGORIES = ["headphones", "earbuds", "smartwatch", "mouse", "keyboard"]


def run_purchase_pipeline(product, quantity=1):
    total = product["price"] * quantity

    # 1. Inventory check
    if product["stock"] < quantity:
        return f"❌ OUT OF STOCK — only {product['stock']} units of {product['name']} available."

    # 2. Quote (mock)
    quote = {"id": "MX-QT-001", "price": total, "quantity": quantity}

    # 3. Policy check
    if total > POLICY_TRANSACTION_LIMIT:
        return (
            f"🟡 PENDING APPROVAL — {product['name']} x{quantity} = ₹{total} "
            f"exceeds the ₹{POLICY_TRANSACTION_LIMIT} auto-approval limit. "
            f"Routed to admin for manual approval."
        )

    # 4. Risk check (mock — always low for demo)
    risk_score = 15

    # 5. Approved -> simulate payment
    return (
        f"✅ APPROVED\n\n"
        f"Product: {product['name']}\n"
        f"Quantity: {quantity}\n"
        f"Total: ₹{total}\n"
        f"Risk Score: {risk_score} (LOW)\n"
        f"Quote ID: {quote['id']}\n\n"
        f"💳 Payment simulated via Razorpay Test Mode — SUCCESS\n"
        f"📋 Logged to audit trail."
    )


# ----------------------------------------------------------------
# MESSAGE HANDLER — wires intent + context + catalog + pipeline
# ----------------------------------------------------------------

def handle_user_message(user_input, memory: AgentMemory):
    intent = detect_intent(user_input)
    step = plan_next_step(intent, user_input, memory)
    memory.log(user_input, intent, step)

    action = step["action"]
    payload = step["payload"]

    if action == "ASK_PRODUCT":
        return "What product would you like?"

    if action == "ASK_ORDER_ID":
        return "Which order ID are you referring to?"

    if action == "SEARCH":
        results = search_products(payload["keyword"], payload.get("budget"))
        memory.remember_search(results, payload.get("budget"), payload.get("quantity"))
        return format_results(results)

    if action == "SEARCH_THEN_BUY":
        results = search_products(payload["keyword"], payload.get("budget"))
        memory.remember_search(results, payload.get("budget"), payload.get("quantity"))
        memory.pending_action = "AWAITING_BUY_CONFIRM"
        return format_results(results) + "\n\nSay **best**, **cheapest**, or the product name to proceed."

    if action == "COMPARE":
        product = payload["product"]
        return f"Comparing against selection: **{product['name']}** — ₹{product['price']}"

    if action == "QUOTE":
        product = payload["product"]
        qty = payload.get("quantity", 1)
        total = product["price"] * qty
        return f"🧾 Quote: {product['name']} x{qty} = ₹{total} (valid 10 min)"

    if action == "INVENTORY":
        product = payload["product"]
        return f"📦 Stock for {product['name']}: {product['stock']} units available."

    if action == "RUN_PURCHASE_PIPELINE":
        return run_purchase_pipeline(payload["product"], payload.get("quantity", 1))

    if action == "HELP":
        return get_agent_response("HELP")

    return get_agent_response(intent)


# ----------------------------------------------------------------
# STREAMLIT UI
# ----------------------------------------------------------------

st.set_page_config(page_title="MERCHX", page_icon="🛡️")

st.title("🛡️ MERCHX")
st.caption("Autonomous AI Commerce Protocol")

# one AgentMemory per browser session
memory = st.session_state.setdefault("memory", AgentMemory())

if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

for entry in st.session_state.chat_log:
    with st.chat_message(entry["role"]):
        st.markdown(entry["text"])

user_input = st.chat_input("Type a command (e.g. headphones, buy, best, cheapest)")

if user_input:
    st.session_state.chat_log.append({"role": "user", "text": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    response = handle_user_message(user_input, memory)

    st.session_state.chat_log.append({"role": "assistant", "text": response})
    with st.chat_message("assistant"):
        st.markdown(response)
