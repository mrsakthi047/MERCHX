import streamlit as st
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
import re

try:
    from google import genai
except ImportError:
    genai = None


st.set_page_config(
    page_title="MERCHX",
    page_icon="🛡️",
    layout="wide"
)

MAX_TRANSACTION = 10000
DAILY_LIMIT = 20000

PRODUCTS = [
    {
        "id": "P001",
        "name": "MERCHX Wireless Headphones",
        "category": "Electronics",
        "price": 7999,
        "stock": 35
    },
    {
        "id": "P002",
        "name": "MERCHX Smart Watch",
        "category": "Electronics",
        "price": 6499,
        "stock": 18
    },
    {
        "id": "P003",
        "name": "MERCHX Mechanical Keyboard",
        "category": "Electronics",
        "price": 4999,
        "stock": 22
    },
    {
        "id": "P004",
        "name": "MERCHX AI Backpack",
        "category": "Accessories",
        "price": 3499,
        "stock": 12
    },
    {
        "id": "P005",
        "name": "MERCHX Pro Laptop",
        "category": "Computers",
        "price": 64999,
        "stock": 7
    }
]


if "audit" not in st.session_state:
    st.session_state.audit = []

if "orders" not in st.session_state:
    st.session_state.orders = []

if "spent" not in st.session_state:
    st.session_state.spent = 0


def money(amount):
    return f"₹{amount:,.0f}"


def log_event(action, status, reason):
    st.session_state.audit.insert(
        0,
        {
            "time": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "action": action,
            "status": status,
            "reason": reason
        }
    )


def search_products(query):
    query = query.lower()
    matches = []

    for product in PRODUCTS:
        text = (
            product["name"]
            + " "
            + product["category"]
        ).lower()

        score = 0

        for word in query.split():
            if len(word) > 2 and word in text:
                score += 1

        if score > 0:
            matches.append((score, product))

    matches.sort(
        key=lambda item: (
            -item[0],
            item[1]["price"]
        )
    )

    if matches:
        return [item[1] for item in matches]

    return PRODUCTS


def extract_budget(text):
    patterns = [
        r"(?:₹|rs|inr|\$)\s*([0-9,]+)",
        r"(?:under|below|within)\s*(?:₹|rs|inr|\$)?\s*([0-9,]+)"
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text.lower()
        )

        if match:
            return int(
                match.group(1).replace(",", "")
            )

    return None


def extract_quantity(text):
    match = re.search(
        r"(?:buy|need|want)\s+(\d+)",
        text.lower()
    )

    if match:
        return max(
            1,
            int(match.group(1))
        )

    match = re.search(
        r"(\d+)\s+(?:units|items|pieces)",
        text.lower()
    )

    if match:
        return max(
            1,
            int(match.group(1))
        )

    return 1


def create_quote(product, quantity):
    now = datetime.now(timezone.utc)

    expires = now + timedelta(
        minutes=10
    )

    quote_id = (
        "MX-QT-"
        + uuid.uuid4().hex[:8].upper()
    )

    raw_data = (
        f"{quote_id}|"
        f"{product['id']}|"
        f"{quantity}|"
        f"{product['price']}|"
        f"{expires.isoformat()}"
    )

    signature = hashlib.sha256(
        raw_data.encode()
    ).hexdigest()

    return {
        "quote_id": quote_id,
        "product_id": product["id"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total": product["price"] * quantity,
        "expires_at": expires.isoformat(),
        "signature": signature
    }


def verify_quote(quote):
    if quote is None:
        return False

    expiry = datetime.fromisoformat(
        quote["expires_at"]
    )

    if datetime.now(timezone.utc) >= expiry:
        return False

    raw_data = (
        f"{quote['quote_id']}|"
        f"{quote['product_id']}|"
        f"{quote['quantity']}|"
        f"{quote['unit_price']}|"
        f"{quote['expires_at']}"
    )

    expected = hashlib.sha256(
        raw_data.encode()
    ).hexdigest()

    return expected == quote["signature"]


def ask_ai(query):
    api_key = st.secrets.get(
        "GEMINI_API_KEY",
        ""
    )

    if not api_key:
        return None

    if genai is None:
        return None

    try:
        client = genai.Client(
            api_key=api_key
        )

        prompt = (
            "You are MERCHX, an AI commerce agent. "
            "Understand this shopping request and "
            "return only the main product keyword: "
            + query
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text.strip()

    except Exception as error:
        log_event(
            "AI",
            "FALLBACK",
            str(error)
        )
        return None


st.title("🛡️ MERCHX")

st.subheader(
    "Autonomous AI Commerce Protocol"
)

st.caption(
    "AI decides • MERCHX authorizes • "
    "Razorpay executes • Audit records"
)


with st.sidebar:

    st.header(
        "MERCHX Control Center"
    )

    st.metric(
        "Transaction Limit",
        money(MAX_TRANSACTION)
    )

    st.metric(
        "Daily Limit",
        money(DAILY_LIMIT)
    )

    st.metric(
        "Spent Today",
        money(st.session_state.spent)
    )

    st.write(
        "Agent ID: AGENT-001"
    )

    st.info(
        "Demo payment is simulated. "
        "No real money is charged."
    )


tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🤖 AI Buyer",
        "🧾 Orders",
        "📋 Audit",
        "🧪 Test Lab"
    ]
)


with tab1:

    st.markdown(
        "### What do you want to buy?"
    )

    query = st.text_input(
        "Product Query",
        placeholder=(
            "Example: wireless headphones "
            "under ₹8000"
        )
    )

    if st.button(
        "🚀 Run MERCHX Agent",
        type="primary"
    ):

        if not query.strip():

            st.warning(
                "Please enter a product requirement."
            )

        else:

            with st.spinner(
                "MERCHX is evaluating the request..."
            ):

                ai_result = ask_ai(query)

                search_text = (
                    ai_result
                    if ai_result
                    else query
                )

                budget = extract_budget(
                    query
                )

                quantity = extract_quantity(
                    query
                )

                candidates = search_products(
                    search_text
                )

                if budget is not None:

                    affordable = [
                        product
                        for product in candidates
                        if product["price"] * quantity
                        <= budget
                    ]

                    if affordable:
                        product = affordable[0]
                    else:
                        product = candidates[0]

                else:

                    product = candidates[0]

                total = (
                    product["price"]
                    * quantity
                )

                quote = create_quote(
                    product,
                    quantity
                )

                quote_valid = verify_quote(
                    quote
                )

                reasons = []

                if total > MAX_TRANSACTION:

                    reasons.append(
                        "Transaction limit exceeded."
                    )

                if (
                    st.session_state.spent
                    + total
                    > DAILY_LIMIT
                ):

                    reasons.append(
                        "Daily spending limit exceeded."
                    )

                if quantity > 3:

                    reasons.append(
                        "Maximum quantity is 3."
                    )

                if quantity > product["stock"]:

                    reasons.append(
                        "Insufficient inventory."
                    )

                if (
                    budget is not None
                    and total > budget
                ):

                    reasons.append(
                        "Product exceeds requested budget."
                    )

                if product["category"] not in [
                    "Electronics",
                    "Accessories"
                ]:

                    reasons.append(
                        "Category is not allowed."
                    )

                risk = "LOW"

                if total >= 9000:
                    risk = "MEDIUM"

                if product["category"] == "Computers":

                    risk = "HIGH"

                    reasons.append(
                        "High-risk computer category."
                    )

                approved = (
                    quote_valid
                    and len(reasons) == 0
                    and risk != "HIGH"
                )

                log_event(
                    "AGENT_DECISION",
                    "APPROVED"
                    if approved
                    else "BLOCKED",
                    "All controls passed."
                    if approved
                    else "; ".join(reasons)
                )

                st.markdown(
                    "### 📋 Protocol Execution Report"
                )

                col1, col2, col3, col4 = st.columns(4)

                col1.metric(
                    "Product",
                    product["name"]
                )

                col2.metric(
                    "Total",
                    money(total)
                )

                col3.metric(
                    "Risk",
                    risk
                )

                col4.metric(
                    "Decision",
                    "APPROVED"
                    if approved
                    else "BLOCKED"
                )

                st.write(
                    "📦 Inventory:",
                    "PASS ✅"
                    if quantity <= product["stock"]
                    else "FAIL ❌"
                )

                st.write(
                    "🧾 Quote:",
                    "VALID ✅"
                    if quote_valid
                    else "INVALID ❌"
                )

                st.write(
                    "🛡️ Policy:",
                    "PASS ✅"
                    if not reasons
                    else "BLOCK ❌"
                )

                st.write(
                    "🚨 Risk:",
                    risk
                )

                if approved:

                    st.success(
                        "AUTHORIZED — Payment boundary reached."
                    )

                    st.info(
                        "💳 Razorpay TEST MODE — SIMULATED"
                    )

                    if st.button(
                        "Confirm Test Payment"
                    ):

                        order_id = (
                            "MX-ORD-"
                            + uuid.uuid4().hex[:8].upper()
                        )

                        order = {
                            "order_id": order_id,
                            "product": product["name"],
                            "amount": total,
                            "status": "PAID",
                            "payment": (
                                "RAZORPAY TEST MODE — "
                                "SIMULATED"
                            )
                        }

                        st.session_state.orders.append(
                            order
                        )

                        st.session_state.spent += total

                        log_event(
                            "CREATE_ORDER",
                            "APPROVED",
                            "All MERCHX controls passed."
                        )

                        st.success(
                            "Payment successful in TEST MODE."
                        )

                        st.json(order)

                else:

                    st.error(
                        "BLOCKED — Payment request was not sent."
                    )

                    for reason in reasons:

                        st.write(
                            "• " + reason
                        )

                st.markdown(
                    "### 🔐 Cryptographic Quote"
                )

                st.json(quote)


with tab2:

    st.subheader(
        "Orders"
    )

    if st.session_state.orders:

        st.dataframe(
            st.session_state.orders,
            use_container_width=True
        )

    else:

        st.info(
            "No orders yet."
        )


with tab3:

    st.subheader(
        "Audit Trail"
    )

    if st.session_state.audit:

        st.dataframe(
            st.session_state.audit,
            use_container_width=True
        )

    else:

        st.info(
            "No audit events yet."
        )


with tab4:

    st.subheader(
        "🧪 MERCHX Test Lab"
    )

    st.write(
        "Test 1: Headphones under ₹8,000 → APPROVE"
    )

    st.write(
        "Test 2: Laptop under ₹10,000 → BLOCK"
    )

    st.write(
        "Test 3: Buy 5 headphones → BLOCK"
    )

    st.write(
        "Test 4: Buy 40 headphones → BLOCK"
    )

    st.success(
        "Run these scenarios from the AI Buyer tab."
    )


st.divider()

st.caption(
    "MERCHX Prototype • Secure AI-native commerce • "
    "Test-safe payment boundary"
)