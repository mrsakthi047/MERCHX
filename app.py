import streamlit as st
import hashlib
import uuid
from datetime import datetime, timedelta

# ============================================================
# OPTIONAL GEMINI AI
# ============================================================

try:
    from google import genai
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="MERCHX — Autonomous AI Commerce Protocol",
    page_icon="🛡️",
    layout="wide"
)


# ============================================================
# MERCHX POLICY CONFIGURATION
# ============================================================

MAX_TRANSACTION = 10000
DAILY_LIMIT = 25000
MAX_QUANTITY = 3


# ============================================================
# SESSION STATE
# ============================================================

if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = []

if "orders" not in st.session_state:
    st.session_state.orders = []

if "processed_requests" not in st.session_state:
    st.session_state.processed_requests = set()


# ============================================================
# PRODUCT CATALOG
# ============================================================

PRODUCTS = [
    {
        "id": "P001",
        "name": "MERCHX Wireless Headphones",
        "category": "Electronics",
        "price": 7999,
        "stock": 35,
        "description": "Wireless noise-cancelling headphones with ANC."
    },
    {
        "id": "P002",
        "name": "MERCHX Smart Watch",
        "category": "Electronics",
        "price": 4999,
        "stock": 18,
        "description": "Smart watch with fitness and notification features."
    },
    {
        "id": "P003",
        "name": "MERCHX Mechanical Keyboard",
        "category": "Electronics",
        "price": 3499,
        "stock": 27,
        "description": "Mechanical keyboard for productivity and gaming."
    },
    {
        "id": "P004",
        "name": "MERCHX Pro Laptop",
        "category": "Electronics",
        "price": 64999,
        "stock": 8,
        "description": "High-performance laptop for professional workloads."
    },
    {
        "id": "P005",
        "name": "MERCHX AI Backpack",
        "category": "Accessories",
        "price": 2999,
        "stock": 12,
        "description": "Smart everyday backpack with multiple compartments."
    }
]


# ============================================================
# AUDIT LOG
# ============================================================

def add_audit(
    action,
    status,
    reason,
    amount=0,
    product="",
    request_id=""
):
    st.session_state.audit_logs.append(
        {
            "timestamp": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "request_id": request_id,
            "action": action,
            "status": status,
            "reason": reason,
            "amount": amount,
            "product": product
        }
    )


# ============================================================
# PRODUCT SEARCH ENGINE
# ============================================================

def search_products(query):
    query = query.lower()
    results = []

    for product in PRODUCTS:
        searchable_text = (
            product["name"]
            + " "
            + product["category"]
            + " "
            + product["description"]
        ).lower()

        if any(word in searchable_text for word in query.split()):
            results.append(product)

    return results


# ============================================================
# DEMO INTENT DETECTION
# ============================================================

def detect_product(user_query):
    text = user_query.lower()

    if "headphone" in text:
        return "headphones"

    if "watch" in text:
        return "watch"

    if "keyboard" in text:
        return "keyboard"

    if "laptop" in text:
        return "laptop"

    if "backpack" in text:
        return "backpack"

    return text


# ============================================================
# INVENTORY ENGINE
# ============================================================

def check_inventory(product, quantity):
    if product["stock"] >= quantity:
        return True, f"{product['stock']} units available."

    return False, "Insufficient inventory."


# ============================================================
# QUOTE ENGINE
# ============================================================

def create_quote(product, quantity):

    quote_id = (
        "MX-QT-"
        + uuid.uuid4().hex[:8].upper()
    )

    total = product["price"] * quantity

    expiry_time = (
        datetime.now()
        + timedelta(minutes=10)
    )

    quote_payload = (
        quote_id
        + product["id"]
        + str(quantity)
        + str(total)
        + expiry_time.isoformat()
    )

    signature = hashlib.sha256(
        quote_payload.encode()
    ).hexdigest()

    return {
        "quote_id": quote_id,
        "product": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total": total,
        "expires_at": expiry_time,
        "signature": signature
    }


# ============================================================
# QUOTE VERIFICATION
# ============================================================

def verify_quote(quote):

    if datetime.now() > quote["expires_at"]:
        return False, "Quote has expired."

    return True, "Quote is valid."


# ============================================================
# POLICY ENGINE
# ============================================================

def policy_check(product, amount, quantity):

    if amount > MAX_TRANSACTION:
        return (
            False,
            f"Transaction exceeds the maximum limit of "
            f"₹{MAX_TRANSACTION:,}."
        )

    if quantity > MAX_QUANTITY:
        return (
            False,
            f"Maximum quantity allowed is {MAX_QUANTITY}."
        )

    allowed_categories = [
        "Electronics",
        "Accessories"
    ]

    if product["category"] not in allowed_categories:
        return (
            False,
            "Product category is not permitted."
        )

    return True, "All policy rules passed."


# ============================================================
# RISK ENGINE
# ============================================================

def risk_check(amount):

    if amount >= 9000:
        return (
            "MEDIUM",
            "Transaction is close to the spending limit."
        )

    return (
        "LOW",
        "No abnormal transaction signal detected."
    )


# ============================================================
# AGENT IDENTITY & PERMISSION
# ============================================================

def get_agent():

    return {
        "agent_id": "AGENT-001",
        "name": "MERCHX Shopping Agent",
        "max_transaction": MAX_TRANSACTION,
        "daily_limit": DAILY_LIMIT,
        "allowed_categories": [
            "Electronics",
            "Accessories"
        ]
    }


# ============================================================
# IDEMPOTENCY ENGINE
# ============================================================

def check_idempotency(request_id):

    if request_id in st.session_state.processed_requests:
        return False

    st.session_state.processed_requests.add(request_id)

    return True


# ============================================================
# GEMINI AI ENGINE
# ============================================================

def ask_gemini(user_query):

    if not GEMINI_SDK_AVAILABLE:
        return None, "Gemini SDK is unavailable."

    try:

        api_key = st.secrets.get(
            "GEMINI_API_KEY"
        )

        if not api_key:
            return None, "Gemini API key is not configured."

        client = genai.Client(
            api_key=api_key
        )

        prompt = f"""
You are MERCHX, an autonomous AI commerce buyer.

User request:
{user_query}

Understand the procurement intent.

Return:
1. Product requested
2. Budget if mentioned
3. Quantity if mentioned
4. Important requirements
5. Short explanation of the purchasing intent

Important:
You do NOT authorize payment.
You do NOT claim payment was completed.
MERCHX policy and risk engines make authorization decisions.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text, None

    except Exception as error:
        return None, str(error)


# ============================================================
# HEADER
# ============================================================

st.title("🛡️ MERCHX")

st.subheader(
    "Autonomous AI Commerce Protocol"
)

st.caption(
    "AI decides. MERCHX authorizes. "
    "Razorpay executes. Every decision is auditable."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("MERCHX Control Center")

    st.metric(
        "Transaction Limit",
        f"₹{MAX_TRANSACTION:,}"
    )

    st.metric(
        "Daily Limit",
        f"₹{DAILY_LIMIT:,}"
    )

    st.divider()

    st.subheader("Agent Identity")

    st.code(
        "AGENT-001\n"
        "MERCHX Shopping Agent"
    )

    st.divider()

    gemini_configured = (
        GEMINI_SDK_AVAILABLE
        and "GEMINI_API_KEY" in st.secrets
    )

    if gemini_configured:
        st.success("Gemini AI: CONNECTED")
    else:
        st.warning("Gemini AI: DEMO MODE")

    st.caption(
        "Demo Mode keeps the MERCHX deterministic "
        "commerce engine functional."
    )


# ============================================================
# TABS
# ============================================================

buyer_tab, products_tab, audit_tab, control_tab = st.tabs(
    [
        "🧠 AI Buyer",
        "📦 Products",
        "📋 Audit Log",
        "📊 Control Center"
    ]
)


# ============================================================
# AI BUYER
# ============================================================

with buyer_tab:

    st.header("AI Procurement Request")

    user_query = st.text_input(
        "What would you like to purchase?",
        placeholder="Example: I need headphones under ₹8,000"
    )

    quantity = st.number_input(
        "Quantity",
        min_value=1,
        max_value=10,
        value=1
    )

    run_agent = st.button(
        "🚀 Run MERCHX Agent",
        type="primary",
        use_container_width=True
    )

    if run_agent:

        if not user_query.strip():

            st.warning(
                "Please enter a valid product requirement."
            )

        else:

            request_id = (
                "REQ-"
                + uuid.uuid4().hex[:10].upper()
            )

            # ------------------------------------------------
            # IDEMPOTENCY
            # ------------------------------------------------

            if not check_idempotency(request_id):

                st.error(
                    "Duplicate request detected."
                )

                st.stop()

            # ------------------------------------------------
            # AI INTENT
            # ------------------------------------------------

            with st.spinner(
                "MERCHX AI is understanding your request..."
            ):

                ai_response, ai_error = ask_gemini(
                    user_query
                )

            if ai_response:

                st.success(
                    "🧠 Gemini AI Connected"
                )

                with st.expander(
                    "AI Procurement Interpretation",
                    expanded=True
                ):
                    st.write(ai_response)

            else:

                st.info(
                    "🎭 Gemini unavailable. "
                    "MERCHX is running in Demo Mode."
                )

            # ------------------------------------------------
            # PRODUCT DISCOVERY
            # ------------------------------------------------

            search_term = detect_product(
                user_query
            )

            products = search_products(
                search_term
            )

            if not products:

                st.error(
                    "No matching product found."
                )

                add_audit(
                    action="PRODUCT_SEARCH",
                    status="BLOCKED",
                    reason="No matching product found.",
                    request_id=request_id
                )

                st.stop()

            product = products[0]

            st.subheader(
                "🛍️ Product Selected"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Product",
                product["name"]
            )

            col2.metric(
                "Price",
                f"₹{product['price']:,}"
            )

            col3.metric(
                "Stock",
                product["stock"]
            )

            st.caption(
                product["description"]
            )

            # ------------------------------------------------
            # INVENTORY
            # ------------------------------------------------

            inventory_ok, inventory_reason = (
                check_inventory(
                    product,
                    quantity
                )
            )

            if inventory_ok:

                st.success(
                    f"📦 Inventory PASS — {inventory_reason}"
                )

            else:

                st.error(
                    f"📦 Inventory BLOCKED — "
                    f"{inventory_reason}"
                )

                add_audit(
                    action="INVENTORY_CHECK",
                    status="BLOCKED",
                    reason=inventory_reason,
                    product=product["name"],
                    request_id=request_id
                )

                st.stop()

            # ------------------------------------------------
            # QUOTE
            # ------------------------------------------------

            quote = create_quote(
                product,
                quantity
            )

            st.subheader(
                "🧾 Commerce Quote"
            )

            q1, q2, q3 = st.columns(3)

            q1.metric(
                "Quote ID",
                quote["quote_id"]
            )

            q2.metric(
                "Total",
                f"₹{quote['total']:,}"
            )

            q3.metric(
                "Validity",
                "10 minutes"
            )

            # ------------------------------------------------
            # QUOTE VERIFICATION
            # ------------------------------------------------

            quote_ok, quote_reason = (
                verify_quote(quote)
            )

            if quote_ok:

                st.success(
                    f"🔐 Quote Verification PASS — "
                    f"{quote_reason}"
                )

            else:

                st.error(
                    f"🔐 Quote Verification FAILED — "
                    f"{quote_reason}"
                )

                add_audit(
                    action="QUOTE_VERIFICATION",
                    status="BLOCKED",
                    reason=quote_reason,
                    amount=quote["total"],
                    product=product["name"],
                    request_id=request_id
                )

                st.stop()

            # ------------------------------------------------
            # POLICY ENGINE
            # ------------------------------------------------

            st.subheader(
                "🛡️ Policy Engine"
            )

            policy_ok, policy_reason = (
                policy_check(
                    product,
                    quote["total"],
                    quantity
                )
            )

            if policy_ok:

                st.success(
                    f"POLICY PASS — {policy_reason}"
                )

            else:

                st.error(
                    f"POLICY BLOCKED — {policy_reason}"
                )

                add_audit(
                    action="POLICY_CHECK",
                    status="BLOCKED",
                    reason=policy_reason,
                    amount=quote["total"],
                    product=product["name"],
                    request_id=request_id
                )

                st.stop()

            # ------------------------------------------------
            # RISK ENGINE
            # ------------------------------------------------

            st.subheader(
                "🚨 Risk Engine"
            )

            risk_level, risk_reason = (
                risk_check(
                    quote["total"]
                )
            )

            if risk_level == "LOW":

                st.success(
                    f"LOW RISK — {risk_reason}"
                )

            else:

                st.warning(
                    f"{risk_level} RISK — {risk_reason}"
                )

            # ------------------------------------------------
            # AGENT PERMISSION
            # ------------------------------------------------

            st.subheader(
                "👤 Agent Permission"
            )

            agent = get_agent()

            if quote["total"] <= agent["max_transaction"]:

                st.success(
                    f"{agent['agent_id']} is authorized "
                    "for this transaction."
                )

            else:

                st.error(
                    "Agent spending permission exceeded."
                )

                add_audit(
                    action="AGENT_PERMISSION",
                    status="BLOCKED",
                    reason="Agent spending permission exceeded.",
                    amount=quote["total"],
                    product=product["name"],
                    request_id=request_id
                )

                st.stop()

            # ------------------------------------------------
            # FINAL AUTHORIZATION
            # ------------------------------------------------

            st.divider()

            st.subheader(
                "🔐 MERCHX Authorization"
            )

            st.success(
                "✅ APPROVED"
            )

            st.write(
                "AI selected the product. "
                "MERCHX independently validated "
                "inventory, quote, policy, risk "
                "and agent permissions."
            )

            # ------------------------------------------------
            # PAYMENT ENCLAVE
            # ------------------------------------------------

            st.subheader(
                "💳 Payment Enclave"
            )

            st.info(
                "The AI agent does not receive direct "
                "payment credentials or payment authority."
            )

            create_order = st.button(
                "💳 Create Razorpay Test Order",
                use_container_width=True
            )

            if create_order:

                order_id = (
                    "MX-ORD-"
                    + uuid.uuid4().hex[:8].upper()
                )

                st.session_state.orders.append(
                    {
                        "order_id": order_id,
                        "quote_id": quote["quote_id"],
                        "product": product["name"],
                        "amount": quote["total"],
                        "status": "TEST_ORDER_CREATED"
                    }
                )

                add_audit(
                    action="CREATE_ORDER",
                    status="APPROVED",
                    reason=(
                        "MERCHX authorization passed."
                    ),
                    amount=quote["total"],
                    product=product["name"],
                    request_id=request_id
                )

                st.success(
                    "✅ Test Commerce Order Created"
                )

                st.code(
                    order_id
                )

                st.caption(
                    "Razorpay Checkout integration will "
                    "be connected in the next integration stage."
                )


# ============================================================
# PRODUCT CATALOG
# ============================================================

with products_tab:

    st.header(
        "📦 MERCHX Product Catalog"
    )

    for product in PRODUCTS:

        with st.container(border=True):

            c1, c2, c3, c4 = st.columns(4)

            c1.write(
                f"**{product['name']}**"
            )

            c2.write(
                f"₹{product['price']:,}"
            )

            c3.write(
                f"Stock: {product['stock']}"
            )

            c4.write(
                product["category"]
            )

            st.caption(
                product["description"]
            )


# ============================================================
# AUDIT LOG
# ============================================================

with audit_tab:

    st.header(
        "📋 MERCHX Audit Trail"
    )

    if not st.session_state.audit_logs:

        st.info(
            "No transactions recorded yet."
        )

    else:

        for log in reversed(
            st.session_state.audit_logs
        ):

            with st.container(border=True):

                st.write(
                    f"**{log['action']}** — "
                    f"{log['status']}"
                )

                st.caption(
                    f"{log['timestamp']} | "
                    f"{log['request_id']}"
                )

                st.write(
                    log["reason"]
                )

                if log["amount"]:

                    st.write(
                        f"Amount: ₹{log['amount']:,}"
                    )

                if log["product"]:

                    st.write(
                        f"Product: {log['product']}"
                    )


# ============================================================
# CONTROL CENTER
# ============================================================

with control_tab:

    st.header(
        "📊 MERCHX Control Center"
    )

    total_orders = len(
        st.session_state.orders
    )

    total_events = len(
        st.session_state.audit_logs
    )

    approved = sum(
        1
        for log in st.session_state.audit_logs
        if log["status"] == "APPROVED"
    )

    blocked = sum(
        1
        for log in st.session_state.audit_logs
        if log["status"] == "BLOCKED"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Orders",
        total_orders
    )

    c2.metric(
        "Audit Events",
        total_events
    )

    c3.metric(
        "Approved",
        approved
    )

    c4.metric(
        "Blocked",
        blocked
    )

    st.divider()

    st.subheader(
        "MERCHX Architecture"
    )

    st.code(
        """
USER
  ↓
GEN AI BUYER 🧠
  ↓
PRODUCT ENGINE
  ↓
INVENTORY 📦
  ↓
QUOTE 🧾
  ↓
QUOTE VERIFICATION 🔐
  ↓
POLICY ENGINE 🛡️
  ↓
RISK ENGINE 🚨
  ↓
AGENT PERMISSION 👤
  ↓
IDEMPOTENCY 🔁
  ↓
PAYMENT ENCLAVE 💳
  ↓
RAZORPAY TEST MODE
  ↓
ORDER
  ↓
AUDIT LOG 📋
        """
    )

    st.success(
        "🧠 AI decides"
    )

    st.info(
        "🛡️ MERCHX authorizes"
    )

    st.warning(
        "💳 Razorpay executes"
    )

    st.write(
        "📋 MERCHX records every important decision."
    )
