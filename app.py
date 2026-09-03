import streamlit as st
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

try:
    from google import genai
except ImportError:
    genai = None

from commerce_engine import (
    search_products,
    check_inventory,
    get_product,
)

from policy_engine import evaluate_policy


# ==================================================
# CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="MERCHX",
    page_icon="🛡️",
    layout="wide",
)

DAILY_LIMIT = 20000


# ==================================================
# PRODUCT CATALOG
# ==================================================

PRODUCTS = [
    {
        "id": "MX-P001",
        "name": "MERCHX Wireless ANC Headphones",
        "category": "Electronics",
        "price": 7499,
        "stock": 35,
        "features": [
            "ANC",
            "Bluetooth",
            "Wireless",
            "40-hour battery",
        ],
    },
    {
        "id": "MX-P002",
        "name": "MERCHX Premium Wireless Headphones",
        "category": "Electronics",
        "price": 8999,
        "stock": 12,
        "features": [
            "ANC",
            "Bluetooth",
            "Wireless",
            "30-hour battery",
        ],
    },
    {
        "id": "MX-P003",
        "name": "MERCHX Smart Watch",
        "category": "Electronics",
        "price": 5999,
        "stock": 20,
        "features": [
            "AMOLED",
            "Fitness Tracking",
            "Bluetooth",
        ],
    },
    {
        "id": "MX-P004",
        "name": "MERCHX Mechanical Keyboard",
        "category": "Electronics",
        "price": 4499,
        "stock": 18,
        "features": [
            "RGB",
            "Mechanical Switches",
            "USB-C",
        ],
    },
    {
        "id": "MX-P005",
        "name": "MERCHX Business Laptop",
        "category": "Computers",
        "price": 64999,
        "stock": 8,
        "features": [
            "16GB RAM",
            "512GB SSD",
            "Intel Processor",
        ],
    },
]


# ==================================================
# SESSION STATE
# ==================================================

if "audit" not in st.session_state:
    st.session_state.audit = []

if "orders" not in st.session_state:
    st.session_state.orders = []

if "spent" not in st.session_state:
    st.session_state.spent = 0


# ==================================================
# HELPERS
# ==================================================

def money(amount):
    return f"₹{amount:,.0f}"


def log_event(action, status, reason):

    st.session_state.audit.insert(
        0,
        {
            "time": datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "action": action,
            "status": status,
            "reason": reason,
        },
    )


def extract_budget(query):

    import re

    patterns = [
        r"(?:₹|rs|inr)\s*([0-9,]+)",
        r"(?:under|below|within)\s*"
        r"(?:₹|rs|inr)?\s*([0-9,]+)",
    ]

    query = query.lower()

    for pattern in patterns:

        match = re.search(
            pattern,
            query,
        )

        if match:

            return int(
                match.group(1).replace(
                    ",",
                    "",
                )
            )

    return None


def extract_quantity(query):

    import re

    query = query.lower()

    patterns = [
        r"(?:buy|need|want)\s+(\d+)",
        r"(\d+)\s+(?:units|items|pieces)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            query,
        )

        if match:

            return max(
                1,
                int(match.group(1)),
            )

    return 1


# ==================================================
# QUOTE ENGINE
# ==================================================

def create_quote(
    product,
    quantity,
):

    now = datetime.now(
        timezone.utc
    )

    expires = now + timedelta(
        minutes=10
    )

    quote_id = (
        "MX-QT-"
        + uuid.uuid4()
        .hex[:8]
        .upper()
    )

    data = (
        f"{quote_id}|"
        f"{product['id']}|"
        f"{quantity}|"
        f"{product['price']}|"
        f"{expires.isoformat()}"
    )

    signature = hashlib.sha256(
        data.encode()
    ).hexdigest()

    return {
        "quote_id": quote_id,
        "product_id": product["id"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total": (
            product["price"]
            * quantity
        ),
        "expires_at": expires.isoformat(),
        "signature": signature,
    }


def verify_quote(quote):

    if quote is None:
        return False

    expiry = datetime.fromisoformat(
        quote["expires_at"]
    )

    if datetime.now(
        timezone.utc
    ) >= expiry:

        return False

    data = (
        f"{quote['quote_id']}|"
        f"{quote['product_id']}|"
        f"{quote['quantity']}|"
        f"{quote['unit_price']}|"
        f"{quote['expires_at']}"
    )

    expected = hashlib.sha256(
        data.encode()
    ).hexdigest()

    return (
        expected
        == quote["signature"]
    )


# ==================================================
# GEMINI AI BUYER
# ==================================================

def ask_ai(query):

    api_key = st.secrets.get(
        "GEMINI_API_KEY",
        "",
    )

    if not api_key or genai is None:
        return None

    try:

        client = genai.Client(
            api_key=api_key
        )

        catalog = ""

        for product in PRODUCTS:

            catalog += (
                f"ID: {product['id']} | "
                f"Name: {product['name']} | "
                f"Category: {product['category']} | "
                f"Price: ₹{product['price']} | "
                f"Stock: {product['stock']} | "
                f"Features: "
                f"{', '.join(product['features'])}\n"
            )

        prompt = f"""
You are the MERCHX AI Buyer.

Understand the user's shopping request.

Select the single best matching product
ONLY from the catalog.

Rules:

1. Never invent products.
2. Never invent prices.
3. Never invent stock.
4. Respect the user's budget.
5. Return ONLY the Product ID.
6. If no suitable product exists, return NONE.

CATALOG:

{catalog}

USER REQUEST:

{query}

Return only a Product ID.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        result = response.text.strip()

        valid_ids = [
            product["id"]
            for product in PRODUCTS
        ]

        if result in valid_ids:
            return result

        return None

    except Exception as error:

        log_event(
            "AI_AGENT",
            "ERROR",
            str(error),
        )

        return None


# ==================================================
# HEADER
# ==================================================

st.title("🛡️ MERCHX")

st.subheader(
    "Autonomous AI Commerce Protocol"
)

st.caption(
    "AI decides • MERCHX authorizes • "
    "Razorpay executes • Audit records"
)


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.header(
        "⚙️ MERCHX Control Center"
    )

    st.metric(
        "Daily Limit",
        money(DAILY_LIMIT),
    )

    st.metric(
        "Spent Today",
        money(
            st.session_state.spent
        ),
    )

    st.divider()

    st.write(
        "**Agent ID:** AGENT-001"
    )

    st.write(
        "**Protocol:** MERCHX v1"
    )

    st.write(
        "**Payment:** Test Mode"
    )

    st.info(
        "No real money is charged."
    )


# ==================================================
# TABS
# ==================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🤖 AI Buyer",
        "🧾 Orders",
        "📋 Audit",
        "🧪 Test Lab",
    ]
)


# ==================================================
# AI BUYER
# ==================================================

with tab1:

    st.header(
        "🤖 MERCHX AI Buyer"
    )

    query = st.text_input(
        "What do you want to buy?",
        placeholder=(
            "Example: wireless headphones "
            "under ₹8000"
        ),
    )

    run_agent = st.button(
        "🚀 Run MERCHX Agent",
        type="primary",
        use_container_width=True,
    )

    if run_agent:

        if not query.strip():

            st.warning(
                "Please enter a product requirement."
            )

        else:

            with st.spinner(
                "MERCHX AI is evaluating..."
            ):

                # 1. UNDERSTAND REQUEST

                budget = extract_budget(
                    query
                )

                quantity = extract_quantity(
                    query
                )

                # 2. AI PRODUCT SELECTION

                ai_product_id = ask_ai(
                    query
                )

                product = None

                if ai_product_id:

                    product = get_product(
                        ai_product_id
                    )

                # 3. FALLBACK SEARCH

                if product is None:

                    candidates = search_products(
                        query,
                        max_price=budget,
                    )

                    if candidates:

                        product = candidates[0]

                if product is None:

                    st.error(
                        "No suitable product found."
                    )

                    log_event(
                        "PRODUCT_SEARCH",
                        "BLOCKED",
                        "No matching product.",
                    )

                    st.stop()

                # 4. INVENTORY

                inventory = check_inventory(
                    product["id"],
                    quantity,
                )

                # 5. QUOTE

                quote = create_quote(
                    product,
                    quantity,
                )

                quote_valid = verify_quote(
                    quote
                )

                # 6. POLICY ENGINE

                policy = evaluate_policy(
                    product=product,
                    quantity=quantity,
                    budget=budget,
                    spent_today=(
                        st.session_state.spent
                    ),
                )

                # 7. RISK ENGINE

                risk = "LOW"

                if policy["total"] >= 9000:

                    risk = "MEDIUM"

                if product["category"] == "Computers":

                    risk = "HIGH"

                # 8. FINAL DECISION

                approved = (
                    policy["approved"]
                    and inventory["available"]
                    and quote_valid
                    and risk != "HIGH"
                )

                # --------------------------------
                # EXECUTION REPORT
                # --------------------------------

                st.markdown(
                    "### 📋 Protocol Execution Report"
                )

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "Product",
                    product["name"],
                )

                c2.metric(
                    "Total",
                    money(
                        policy["total"]
                    ),
                )

                c3.metric(
                    "Risk",
                    risk,
                )

                c4.metric(
                    "Decision",
                    (
                        "APPROVED"
                        if approved
                        else "BLOCKED"
                    ),
                )

                st.divider()

                st.write(
                    "🤖 **AI Selection:**",
                    ai_product_id
                    or "Fallback Search",
                )

                st.write(
                    "📦 **Inventory:**",
                    (
                        "PASS ✅"
                        if inventory["available"]
                        else "FAIL ❌"
                    ),
                )

                st.write(
                    "🧾 **Quote:**",
                    (
                        "VALID ✅"
                        if quote_valid
                        else "INVALID ❌"
                    ),
                )

                st.write(
                    "🛡️ **Policy:**",
                    (
                        "PASS ✅"
                        if policy["approved"]
                        else "BLOCK ❌"
                    ),
                )

                st.write(
                    "🚨 **Risk:**",
                    risk,
                )

                # --------------------------------
                # POLICY DETAILS
                # --------------------------------

                st.markdown(
                    "### 🛡️ Policy Checks"
                )

                for check, result in (
                    policy["checks"].items()
                ):

                    icon = (
                        "✅"
                        if result == "PASS"
                        else "❌"
                    )

                    st.write(
                        f"{icon} "
                        f"{check.replace('_', ' ').title()}: "
                        f"{result}"
                    )

                # --------------------------------
                # FINAL DECISION
                # --------------------------------

                if approved:

                    st.success(
                        "AUTHORIZED — "
                        "Payment boundary reached."
                    )

                    st.info(
                        "💳 Razorpay TEST MODE — "
                        "SIMULATED"
                    )

                    if st.button(
                        "💳 Confirm Test Payment",
                        type="primary",
                    ):

                        order_id = (
                            "MX-ORD-"
                            + uuid.uuid4()
                            .hex[:8]
                            .upper()
                        )

                        order = {
                            "order_id": order_id,
                            "product": product["name"],
                            "product_id": product["id"],
                            "quantity": quantity,
                            "amount": policy["total"],
                            "status": "PAID",
                            "payment": (
                                "RAZORPAY TEST MODE"
                            ),
                        }

                        st.session_state.orders.append(
                            order
                        )

                        st.session_state.spent += (
                            policy["total"]
                        )

                        log_event(
                            "PAYMENT",
                            "APPROVED",
                            "All MERCHX controls passed.",
                        )

                        st.success(
                            "Payment successful "
                            "in TEST MODE."
                        )

                        st.json(order)

                else:

                    st.error(
                        "BLOCKED — Payment request "
                        "was NOT sent."
                    )

                    for reason in policy["reasons"]:

                        st.write(
                            "❌ " + reason
                        )

                    if risk == "HIGH":

                        st.write(
                            "❌ High-risk transaction."
                        )

                    log_event(
                        "TRANSACTION",
                        "BLOCKED",
                        "; ".join(
                            policy["reasons"]
                        )
                        or "Risk policy blocked transaction.",
                    )

                # --------------------------------
                # QUOTE
                # --------------------------------

                st.markdown(
                    "### 🔐 Cryptographic Quote"
                )

                st.json(quote)


# ==================================================
# ORDERS
# ==================================================

with tab2:

    st.header(
        "🧾 MERCHX Orders"
    )

    if st.session_state.orders:

        st.dataframe(
            st.session_state.orders,
            use_container_width=True,
        )

    else:

        st.info(
            "No orders yet."
        )


# ==================================================
# AUDIT
# ==================================================

with tab3:

    st.header(
        "📋 MERCHX Audit Trail"
    )

    if st.session_state.audit:

        st.dataframe(
            st.session_state.audit,
            use_container_width=True,
        )

    else:

        st.info(
            "No audit events yet."
        )


# ==================================================
# TEST LAB
# ==================================================

with tab4:

    st.header(
        "🧪 MERCHX Security Test Lab"
    )

    st.write(
        "### Test 1 — Normal Purchase"
    )

    st.code(
        "wireless headphones under ₹8000"
    )

    st.write(
        "Expected: APPROVED ✅"
    )

    st.divider()

    st.write(
        "### Test 2 — Budget Violation"
    )

    st.code(
        "laptop under ₹10000"
    )

    st.write(
        "Expected: BLOCKED 🛡️"
    )

    st.divider()

    st.write(
        "### Test 3 — Quantity Violation"
    )

    st.code(
        "buy 5 wireless headphones"
    )

    st.write(
        "Expected: BLOCKED 🛡️"
    )

    st.divider()

    st.write(
        "### Test 4 — Inventory Violation"
    )

    st.code(
        "buy 40 wireless headphones"
    )

    st.write(
        "Expected: BLOCKED 🛡️"
    )

    st.divider()

    st.success(
        "Independent MERCHX Policy Engine active."
    )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "MERCHX • Secure AI-Native Commerce Protocol • "
    "Policy-Controlled Payment Boundary"
)