import streamlit as st
import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone

# Optional Gemini SDK
try:
    from google import genai
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False


# =========================================================
# MERCHX CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="MERCHX — Autonomous AI Commerce Protocol",
    page_icon="🛡️",
    layout="wide",
)

MAX_TRANSACTION = 10000
DAILY_LIMIT = 20000
QUOTE_MINUTES = 10


# =========================================================
# DEMO PRODUCT CATALOG
# =========================================================

PRODUCTS = [
    {
        "id": "P001",
        "name": "MERCHX Wireless Headphones",
        "category": "Electronics",
        "price": 7999,
        "stock": 35,
        "rating": 4.6,
        "features": ["ANC", "Bluetooth 5.3", "40h battery"],
    },
    {
        "id": "P002",
        "name": "MERCHX Smart Watch",
        "category": "Electronics",
        "price": 6499,
        "stock": 18,
        "rating": 4.4,
        "features": ["AMOLED", "GPS", "Health tracking"],
    },
    {
        "id": "P003",
        "name": "MERCHX Mechanical Keyboard",
        "category": "Electronics",
        "price": 4999,
        "stock": 22,
        "rating": 4.7,
        "features": ["Hot-swap", "RGB", "Wireless"],
    },
    {
        "id": "P004",
        "name": "MERCHX AI Backpack",
        "category": "Accessories",
        "price": 3499,
        "stock": 12,
        "rating": 4.3,
        "features": ["USB charging", "Laptop sleeve", "Water resistant"],
    },
    {
        "id": "P005",
        "name": "MERCHX Pro Laptop",
        "category": "Computers",
        "price": 64999,
        "stock": 7,
        "rating": 4.8,
        "features": ["16GB RAM", "512GB SSD", "14-inch display"],
    },
]


# =========================================================
# SESSION STATE
# =========================================================

if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = []

if "orders" not in st.session_state:
    st.session_state.orders = []

if "spent_today" not in st.session_state:
    st.session_state.spent_today = 0

if "last_quote" not in st.session_state:
    st.session_state.last_quote = None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def money(value):
    return f"₹{value:,.0f}"


def audit(action, status, reason, **extra):
    st.session_state.audit_logs.insert(
        0,
        {
            "timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            ),
            "action": action,
            "status": status,
            "reason": reason,
            **extra,
        },
    )


def find_products(query):
    query = query.lower()

    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", query)
        if len(token) > 2
    ]

    scored = []

    for product in PRODUCTS:

        searchable_text = " ".join(
            [
                product["name"],
                product["category"],
                *product["features"],
            ]
        ).lower()

        score = sum(
            1 for token in tokens if token in searchable_text
        )

        if score:
            scored.append((score, product))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1]["price"],
        )
    )

    return [product for _, product in scored] or PRODUCTS


def extract_budget(text):

    patterns = [
        r"(?:₹|rs\.?|inr|\$)\s*([0-9][0-9,]*)",
        r"([0-9][0-9,]*)\s*(?:rupees|rs)\b",
        r"under\s+([0-9][0-9,]*)",
        r"below\s+([0-9][0-9,]*)",
        r"within\s+([0-9][0-9,]*)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text.lower(),
        )

        if match:
            return int(
                match.group(1).replace(",", "")
            )

    return None


def extract_quantity(text):

    match = re.search(
        r"\b(?:qty|quantity|buy|need|want)\s*(?:of\s*)?(\d+)\b",
        text.lower(),
    )

    if match:
        return max(
            1,
            min(int(match.group(1)), 20),
        )

    match = re.search(
        r"\b(\d+)\s*(?:units?|items?|pieces?)\b",
        text.lower(),
    )

    if match:
        return max(
            1,
            min(int(match.group(1)), 20),
        )

    return 1


# =========================================================
# QUOTE CREATION
# =========================================================

def create_quote(product, quantity):

    now = datetime.now(timezone.utc)

    expires = now + timedelta(
        minutes=QUOTE_MINUTES
    )

    quote_id = (
        "MX-QT-"
        + uuid.uuid4().hex[:8].upper()
    )

    payload = {
        "quote_id": quote_id,
        "product_id": product["id"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total": product["price"] * quantity,
        "expires_at": expires.isoformat(),
    }

    signature = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    payload["signature"] = signature

    return payload


# =========================================================
# QUOTE VERIFICATION
# =========================================================

def secure_compare(a, b):

    if len(a) != len(b):
        return False

    result = 0

    for x, y in zip(
        a.encode(),
        b.encode(),
    ):
        result |= x ^ y

    return result == 0


def verify_quote(quote):

    if not quote:
        return False, "No quote exists."

    try:

        expires = datetime.fromisoformat(
            quote["expires_at"]
        )

        if datetime.now(timezone.utc) >= expires:
            return False, "Quote expired."

    except Exception:

        return False, "Invalid quote expiry."

    unsigned_quote = {
        key: quote[key]
        for key in quote
        if key != "signature"
    }

    expected_signature = hashlib.sha256(
        json.dumps(
            unsigned_quote,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    if not secure_compare(
        expected_signature,
        quote.get("signature", ""),
    ):
        return False, "Quote signature verification failed."

    return True, "Quote valid."


# =========================================================
# POLICY ENGINE
# =========================================================

def policy_check(
    product,
    quantity,
    total,
):

    reasons = []

    if total > MAX_TRANSACTION:

        reasons.append(
            f"Transaction limit exceeded "
            f"({money(total)} > {money(MAX_TRANSACTION)})."
        )

    if (
        st.session_state.spent_today + total
        > DAILY_LIMIT
    ):

        reasons.append(
            "Daily spending limit would be exceeded."
        )

    if product["category"] not in {
        "Electronics",
        "Accessories",
    }:

        reasons.append(
            "Category is not allowed by the demo policy."
        )

    if quantity > 3:

        reasons.append(
            "Maximum quantity per transaction is 3."
        )

    if quantity > product["stock"]:

        reasons.append(
            "Insufficient inventory."
        )

    return (
        len(reasons) == 0,
        reasons,
    )


# =========================================================
# RISK ENGINE
# =========================================================

def risk_check(
    product,
    quantity,
    total,
):

    risk = "LOW"
    reasons = []

    if total >= 9000:

        risk = "MEDIUM"

        reasons.append(
            "High-value transaction."
        )

    if quantity >= 3:

        risk = "MEDIUM"

        reasons.append(
            "Bulk quantity."
        )

    if product["category"] == "Computers":

        risk = "HIGH"

        reasons.append(
            "High-value computer category."
        )

    return risk, reasons


# =========================================================
# GEMINI AI AGENT
# =========================================================

def ask_gemini(user_query):

    api_key = st.secrets.get(
        "GEMINI_API_KEY",
        "",
    )

    if not api_key or not GEMINI_SDK_AVAILABLE:
        return None

    try:

        client = genai.Client(
            api_key=api_key
        )

        prompt = f"""
You are MERCHX, an AI-native commerce agent.

Parse this procurement request:

{user_query!r}

Return ONLY valid JSON.

Required keys:

product_keywords
budget
quantity

Rules:

product_keywords = product requested by user
budget = numeric budget or null
quantity = integer

Do not invent products.
This is a demo catalog.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        text = response.text.strip()

        text = re.sub(
            r"^```json\s*|\s*```$",
            "",
            text,
            flags=re.I,
        )

        return json.loads(text)

    except Exception as error:

        audit(
            "AI_PARSE",
            "FALLBACK",
            f"Gemini unavailable: {str(error)[:160]}",
        )

        return None


def parse_request(user_query):

    ai_data = ask_gemini(
        user_query
    )

    if ai_data:

        keywords = str(
            ai_data.get(
                "product_keywords",
                user_query,
            )
        )

        budget = ai_data.get(
            "budget"
        )

        quantity = int(
            ai_data.get(
                "quantity",
                1,
            )
            or 1
        )

        return (
            keywords,
            budget,
            max(
                1,
                min(quantity, 20),
            ),
            "Gemini AI",
        )

    return (
        user_query,
        extract_budget(user_query),
        extract_quantity(user_query),
        "Deterministic fallback",
    )


# =========================================================
# PAYMENT / IDEMPOTENCY
# =========================================================

def execute_purchase(
    product,
    quote,
):

    request_id = (
        "REQ-"
        + uuid.uuid4().hex[:10].upper()
    )

    idempotency_key = (
        f"{quote['quote_id']}:"
        f"{product['id']}:"
        f"{quote['quantity']}"
    )

    existing_order = next(
        (
            order
            for order in st.session_state.orders
            if order["idempotency_key"]
            == idempotency_key
        ),
        None,
    )

    if existing_order:

        audit(
            "PAYMENT",
            "DUPLICATE_BLOCKED",
            "Idempotency key already processed.",
            request_id=request_id,
        )

        return existing_order, "duplicate"

    order_id = (
        "MX-ORD-"
        + uuid.uuid4().hex[:8].upper()
    )

    order = {
        "order_id": order_id,
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "product": product["name"],
        "quantity": quote["quantity"],
        "amount": quote["total"],
        "payment": "RAZORPAY TEST MODE — SIMULATED",
        "status": "PAID",
        "timestamp": datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        ),
    }

    st.session_state.orders.append(
        order
    )

    st.session_state.spent_today += (
        quote["total"]
    )

    audit(
        "CREATE_ORDER",
        "APPROVED",
        "Policy and risk checks passed.",
        order_id=order_id,
        amount=quote["total"],
    )

    return order, "created"


# =========================================================
# MERCHX UI
# =========================================================

st.title("🛡️ MERCHX")

st.subheader(
    "Autonomous AI Commerce Protocol"
)

st.caption(
    "AI decides • MERCHX authorizes • "
    "Razorpay executes • Audit records"
)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.header(
        "🛡️ MERCHX Control Center"
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
        money(
            st.session_state.spent_today
        ),
    )

    st.divider()

    st.write(
        "**Agent Identity**"
    )

    st.code(
        "AGENT-001"
    )

    st.write(
        "Role: Procurement Agent"
    )

    st.write(
        "Allowed: Electronics, Accessories"
    )

    st.write(
        "Max quantity: 3"
    )

    st.divider()

    st.info(
        "Demo mode uses a simulated "
        "Razorpay Test Mode payment boundary. "
        "No real money is charged."
    )


# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🤖 AI Buyer",
        "🧾 Quotes & Orders",
        "📋 Audit Trail",
        "🧪 Test Lab",
    ]
)


# =========================================================
# AI BUYER
# =========================================================

with tab1:

    st.markdown(
        "### What do you want to buy?"
    )

    query = st.text_input(
        "Product requirement",
        placeholder=(
            "Example: I need wireless "
            "headphones under ₹8,000"
        ),
        label_visibility="collapsed",
    )

    if st.button(
        "🚀 Run MERCHX Agent",
        type="primary",
        use_container_width=True,
    ):

        if not query.strip():

            st.warning(
                "Please enter a product requirement."
            )

        else:

            with st.spinner(
                "AI → Search → Inventory → "
                "Quote → Policy → Risk → Authorization..."
            ):

                keywords, budget, quantity, parser = (
                    parse_request(query)
                )

                candidates = find_products(
                    keywords
                )

                product = candidates[0]

                # Budget-aware selection

                if budget is not None:

                    affordable = [
                        p
                        for p in candidates
                        if p["price"] * quantity
                        <= budget
                    ]

                    if affordable:

                        product = sorted(
                            affordable,
                            key=lambda p: (
                                p["price"],
                                -p["rating"],
                            ),
                        )[0]

                total = (
                    product["price"]
                    * quantity
                )

                # Quote

                quote = create_quote(
                    product,
                    quantity,
                )

                st.session_state.last_quote = (
                    quote
                )

                # Verification

                quote_ok, quote_reason = (
                    verify_quote(quote)
                )

                # Policy

                policy_ok, policy_reasons = (
                    policy_check(
                        product,
                        quantity,
                        total,
                    )
                )

                # Risk

                risk, risk_reasons = (
                    risk_check(
                        product,
                        quantity,
                        total,
                    )
                )

                # Budget protection

                if (
                    budget is not None
                    and total > budget
                ):

                    policy_ok = False

                    policy_reasons.append(
                        f"Selected product exceeds "
                        f"requested budget "
                        f"({money(total)} > "
                        f"{money(budget)})."
                    )

                # Authorization

                authorization = (
                    "APPROVED"
                    if (
                        quote_ok
                        and policy_ok
                        and risk != "HIGH"
                    )
                    else "BLOCKED"
                )

                audit(
                    "AGENT_DECISION",
                    authorization,
                    (
                        "; ".join(
                            policy_reasons
                            + risk_reasons
                        )
                        if authorization
                        == "BLOCKED"
                        else "All controls passed."
                    ),
                    product=product["name"],
                    amount=total,
                    parser=parser,
                )

                # Report

                st.markdown(
                    "### 📋 Protocol Execution Report"
                )

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "Selected",
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
                    authorization,
                )

                st.write(
                    "**Product**"
                )

                st.write(
                    f"{product['name']} • "
                    f"{product['category']} • "
                    f"⭐ {product['rating']}"
                )

                st.write(
                    "Features: "
                    + ", ".join(
                        product["features"]
                    )
                )

                st.write(
                    "**Control Checks**"
                )

                st.write(
                    "📦 Inventory: "
                    + (
                        "PASS ✅"
                        if quantity
                        <= product["stock"]
                        else "FAIL ❌"
                    )
                    + f" — {product['stock']} units available"
                )

                st.write(
                    "🧾 Quote: "
                    + (
                        "VALID ✅"
                        if quote_ok
                        else "INVALID ❌"
                    )
                    + f" — `{quote['quote_id']}`"
                )

                st.write(
                    "🛡️ Policy: "
                    + (
                        "PASS ✅"
                        if policy_ok
                        else "BLOCK ❌"
                    )
                )

                st.write(
                    "🚨 Risk: "
                    + risk
                    + (
                        " ✅"
                        if risk != "HIGH"
                        else " ❌"
                    )
                )

                st.write(
                    "👤 Agent Permission: "
                    + (
                        "PASS ✅"
                        if product["category"]
                        in {
                            "Electronics",
                            "Accessories",
                        }
 
