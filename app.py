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

# --------------------------------------------------
# MERCHX CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="MERCHX",
    page_icon="🛡️",
    layout="wide",
)

MAX_TRANSACTION = 10000
DAILY_LIMIT = 20000
MAX_QUANTITY = 3

ALLOWED_CATEGORIES = [
    "Electronics",
    "Accessories",
]

# --------------------------------------------------
# PRODUCT CATALOG
# --------------------------------------------------

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

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "audit" not in st.session_state:
    st.session_state.audit = []

if "orders" not in st.session_state:
    st.session_state.orders = []

if "spent" not in st.session_state:
    st.session_state.spent = 0


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

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
            "reason": reason,
        },
    )


def extract_budget(query):
    import re

    patterns = [
        r"(?:₹|rs|inr)\s*([0-9,]+)",
        r"(?:under|below|within)\s*(?:₹|rs|inr)?\s*([0-9,]+)",
    ]

    query = query.lower()

    for pattern in patterns:
        match = re.search(pattern, query)

        if match:
            return int(
                match.group(1).replace(",", "")
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
        match = re.search(pattern, query)

        if match:
            return max(
                1,
                int(match.group(1))
            )

    return 1


# --------------------------------------------------
# QUOTE ENGINE
# --------------------------------------------------

def create_quote(product, quantity):

    now = datetime.now(timezone.utc)

    expires = now + timedelta(
        minutes=10
    )

    quote_id = (
        "MX-QT-"
        + uuid.uuid4().hex[:8].upper()
    )

    quote_data = (
        f"{quote_id}|"
        f"{product['id']}|"
        f"{quantity}|"
        f"{product['price']}|"
        f"{expires.isoformat()}"
    )

    signature = hashlib.sha256(
        quote_data.encode()
    ).hexdigest()

    return {
        "quote_id": quote_id,
        "product_id": product["id"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total": product["price"] * quantity,
        "expires_at": expires.isoformat(),
        "signature": signature,
    }


def verify_quote(quote):

    if quote is None:
        return False

    expiry = datetime.fromisoformat(
        quote["expires_at"]
    )

    if datetime.now(timezone.utc) >= expiry:
        return False

    quote_data = (
        f"{quote['quote_id']}|"
        f"{quote['product_id']}|"
        f"{quote['quantity']}|"
        f"{quote['unit_price']}|"
        f"{quote['expires_at']}"
    )

    expected_signature = hashlib.sha256(
        quote_data.encode()
    ).hexdigest()

    return (
        expected_signature
        == quote["signature"]
    )


# --------------------------------------------------
# GEMINI AI BUYER
# --------------------------------------------------

def ask_ai(query):

    api_key = st.secrets.get(
        "GEMINI_API_KEY",
        ""
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
ONLY from the catalog below.

Rules:

1. Never invent products.
2. Never invent prices.
3. Never invent stock.
4. Respect the user's budget.
5. Return ONLY the exact Product ID.
6. If no product matches, return NONE.

MERCHX CATALOG:

{catalog}

USER REQUEST:

{query}

Return only:
MX-P001
MX-P002
MX-P003
MX-P004
MX-P005
or NONE.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        result = response.text.strip()

        if result in [
            product["id"]
            for product in PRODUCTS
        ]:
            return result

        return None

    except Exception as error:

        log_event(
            "AI_AGENT",
            "FALLBACK",
            str(error),
        )

        return None


# --------------------------------------------------
# UI HEADER
# --------------------------------------------------

st.title("🛡️ MERCHX")

st.subheader(
    "Autonomous AI Commerce Protocol"
)

st.caption(
    "AI decides • MERCHX authorizes • "
    "Razorpay executes • Audit records"
)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.header(
        "⚙️ MERCHX Control Center"
    )

    st.metric(
        "Transaction Limit",
        money(MAX_TRANSACTION),
    )

    st.metric(
        "Daily Limit",
        money(DAILY_LIMIT),
    )

    st.metric(
        "Spent Today",
        money(st.session_state.spent),
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


# --------------------------------------------------
# TABS
# --------------------------------------------------

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

                # ------------------------------
                # STEP 1: UNDERSTAND REQUEST
                # ------------------------------

                budget = extract_budget(
                    query
                )

                quantity = extract_quantity(
                    query
                )

                # ------------------------------
                # STEP 2: AI PRODUCT SELECTION
                # ------------------------------

                ai_product_id = ask_ai(
                    query
                )

                product = None

                if ai_product_id:

                    product = get_product(
                        ai_product_id
                    )

                # ------------------------------
                # STEP 3: SAFE FALLBACK
                # ------------------------------

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

                # ------------------------------
                # STEP 4: INVENTORY
                # ------------------------------

                inventory = check_inventory(
                    product["id"],
                    quantity,
                )

                # ------------------------------
                # STEP 5: QUOTE
                # ------------------------------

                quote = create_quote(
                    product,
                    quantity,
                )

                quote_valid = verify_quote(
                    quote
                )

                total = (
                    product["price"]
                    * quantity
                )

                # ------------------------------
                # STEP 6: POLICY ENGINE
                # ------------------------------

                policy_reasons = []

                if total > MAX_TRANSACTION:

                    policy_reasons.append(
                        "Transaction limit exceeded."
                    )

                if (
                    st.session_state.spent
                    + total
                    > DAILY_LIMIT
                ):

                    policy_reasons.append(
                        "Daily spending limit exceeded."
                    )

                if quantity > MAX_QUANTITY:

                    policy_reasons.append(
                        "Maximum quantity is 3."
                    )

                if not inventory["available"]:

                    policy_reasons.append(
                        "Insufficient inventory."
                    )

                if (
                    budget is not None
                    and total > budget
                ):

                    policy_reasons.append(
                        "Requested budget exceeded."
                    )

                if (
                    product["category"]
                    not in ALLOWED_CATEGORIES
                ):

                    policy_reasons.append(
                        "Category is not allowed."
                    )

                # ------------------------------
                # STEP 7: RISK ENGINE
                # ------------------------------

                risk = "LOW"

                if total >= 9000:
                    risk = "MEDIUM"

                if (
                    product["category"]
                    == "Computers"
                ):

                    risk = "HIGH"

                    policy_reasons.append(
                        "High-risk computer category."
                    )

                # ------------------------------
                # STEP 8: FINAL AUTHORIZATION
                # ------------------------------

                approved = (
                    quote_valid
                    and inventory["available"]
                    and len(policy_reasons) == 0
                    and risk != "HIGH"
                )

                # ------------------------------
                # EXECUTION REPORT
                # ------------------------------

                st.markdown(
                    "### 📋 Protocol Execution Report"
                )

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "AI Selected",
                    product["name"],
                )

                c2.metric(
                    "Total",
                    money(total),
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
                    "🤖 **AI Product ID:**",
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
                        if not policy_reasons
                        else "BLOCK ❌"
                    ),
                )

                st.write(
                    "🚨 **Risk:**",
                    risk,
                )

                # ------------------------------
                # DECISION
                # ------------------------------

                if approved:

                    st.success(
                        "AUTHORIZED — "
                        "Payment boundary reached."
                    )

                    st.info(
                        "💳 Razorpay TEST MODE — "
                        "SIMULATED"
                    )

                    confirm_payment = st.button(
                        "💳 Confirm Test Payment",
                        type="primary",
                    )

                    if confirm_payment:

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
                            "amount": total,
                            "status": "PAID",
                            "payment": (
                                "RAZORPAY TEST MODE"
                            ),
                        }

                        st.session_state.orders.append(
                            order
                        )

                        st.session_state.spent += total

                        log_event(
                            "PAYMENT",
                            "APPROVED",
                            (
                                "All MERCHX "
                                "controls passed."
                            ),
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

                    for reason in policy_reasons:

                        st.write(
                            "❌ " + reason
                        )

                    log_event(
                        "TRANSACTION",
                        "BLOCKED",
                        "; ".join(
                            policy_reasons
                        ),
                    )

                # ------------------------------
                # QUOTE
                # ------------------------------

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
        "### Test 1"
    )

    st.code(
        "Find wireless headphones under ₹8000"
    )

    st.write(
        "Expected: APPROVED ✅"
    )

    st.divider()

    st.write(
        "### Test 2"
    )

    st.code(
        "I need a laptop under ₹10000"
    )

    st.write(
        "Expected: BLOCKED 🛡️"
    )

    st.divider()

    st.write(
        "### Test 3"
    )

    st.code(
        "Buy 5 wireless headphones"
    )

    st.write(
        "Expected: BLOCKED 🛡️"
    )

    st.divider()

    st.write(
        "### Test 4"
    )

    st.code(
        "Buy 40 wireless headphones"
    )

    st.write(
        "Expected: BLOCKED 🛡️"
    )

    st.divider()

    st.success(
        "MERCHX security boundary is active."
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "MERCHX Prototype • "
    "Secure AI-Native Commerce Protocol • "
    "Razorpay Test-Safe Pay