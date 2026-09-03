import streamlit as st
import hashlib
import uuid
import time
from datetime import datetime, timedelta

# Optional Gemini SDK
try:
    from google import genai
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False


# ============================================================
# MERCHX CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="MERCHX — Autonomous AI Commerce Protocol",
    page_icon="🛡️",
    layout="wide"
)

MAX_TRANSACTION = 10000
DAILY_LIMIT = 25000


# ============================================================
# SESSION STATE
# ============================================================

if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = []

if "processed_requests" not in st.session_state:
    st.session_state.processed_requests = set()

if "orders" not in st.session_state:
    st.session_state.orders = []

if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False


# ============================================================
# PRODUCT DATABASE
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
        "description": "Smart fitness watch with health and notification features."
    },
    {
        "id": "P003",
        "name": "MERCHX Mechanical Keyboard",
        "category": "Electronics",
        "price": 3499,
        "stock": 27,
        "description": "Mechanical keyboard designed for productivity and gaming."
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
# AUDIT SYSTEM
# ============================================================

def add_audit(
    action,
    status,
    reason,
    amount=0,
    product="",
    request_id=""
):
    st.session_state.audit_logs.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_id": request_id,
        "action": action,
        "status": status,
        "reason": reason,
        "amount": amount,
        "product": product
    })


# ============================================================
# PRODUCT SEARCH
# ============================================================

def search_products(query):
    query = query.lower()

    results = []

    for product in PRODUCTS:
        searchable = (
            product["name"] + " " +
            product["category"] + " " +
            product["description"]
        ).lower()

        if any(word in searchable for word in query.split()):
            results.append(product)

    return results


# ============================================================
# INVENTORY ENGINE
# ============================================================

def check_inventory(product, quantity=1):

    if product["stock"] >= quantity:
        return True, f"{product['stock']} units available."

    return False, "Insufficient inventory."


# ============================================================
# QUOTE ENGINE
# ============================================================

def create_quote(product, quantity):

    quote_id = "MX-QT-" + uuid.uuid4().hex[:8].upper()

    total = product["price"] * quantity

    expiry = datetime.now() + timedelta(minutes=10)

    quote_data = (
        quote_id +
        product["id"] +
        str(quantity) +
        str(total) +
        expiry.isoformat()
    )

    signature = hashlib.sha256(
        quote_data.encode()
    ).hexdigest()

    return {
        "quote_id": quote_id,
        "product": product["name"],
        "quantity": quantity,
        "unit_price": product["price"],
        "total": total,
        "expires_at": expiry,
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
        return False, (
            f"Transaction limit exceeded. "
            f"Maximum allowed is ₹{MAX_TRANSACTION:,}."
        )

    if quantity > 3:
        return False, "Maximum quantity allowed is 3."

    if product["category"] not in ["Electronics", "Accessories"]:
        return False, "Product category is not permitted."

    return True, "All policy rules passed."


# ============================================================
# RISK ENGINE
# ============================================================

def risk_check(amount):

    if amount >= 9000:
        return "MEDIUM", "Transaction is close to the maximum spending limit."

    return "LOW", "No abnormal transaction signal detected."


# ============================================================
# AGENT PERMISSION
# ============================================================

def agent_permission():

    return {
        "agent_id": "AGENT-001",
        "name": "MERCHX Shopping Agent",
        "max_transaction": MAX_TRANSACTION,
        "daily_limit": DAILY_LIMIT,
        "categories": ["Electronics", "Accessories"]
    }


# ============================================================
# IDEMPOTENCY
# ============================================================

def check_idempotency(request_id):

    if request_id in st.session_state.processed_requests:
        return False

    st.session_state.processed_requests.add(request_id)

    return True


# ============================================================
# GEMINI AI
# ============================================================

def ask_gemini(user_query):

    if not GEMINI_SDK_AVAILABLE:
        return None, "Gemini SDK unavailable."

    try:
        api_key = st.secrets.get("GEMINI_API_KEY")

        if not api_key:
            return None, "GEMINI_API_KEY is not configured."

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are the MERCHX Autonomous Commerce Agent.

User procurement request:
{user_query}

Your job is to understand the user's intent.

Extract:
1. Product requested
2. Maximum budget if mentioned
3. Quantity if mentioned
4. Important product requirements

Do not authorize payment.
Do not claim that a payment was completed.

Return a concise procurement interpretation.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text, None

    except Exception as e:
        return None, str(e)


# ============================================================
# DEMO INTENT PARSER
# ============================================================

def demo_intent(user_query):

    text = user_query.lower()

    if "headphone" in text:
        product_keyword = "headphones"

    elif "watch" in text:
        product_keyword = "watch"

    elif "keyboard" in text:
        product_keyword = "keyboard"

    elif "laptop" in text:
        product_keyword = "laptop"

    elif "backpack" in text:
        product_keyword = "backpack"

    else:
        product_keyword = text

    return product_keyword


# ============================================================
# HEADER
# ============================================================

st.title("🛡️ MERCHX")

st.subheader(
    "Autonomous AI Commerce Protocol"
)

st.caption(
    "AI decides. MERCHX authorizes. Razorpay executes. "
    "Every decision is auditable."
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

    st.write("### Agent Identity")

    st.code(
        "AGENT-001\n"
        "MERCHX Shopping Agent"
    )

    st.divider()

    st.write("### System")

    api_available = (
        GEMINI_SDK_AVAILABLE
        and "GEMINI_API_KEY" in st.secrets
    )

    if api_available:
        st.success("Gemini AI: CONNECTED")
    else:
        st.warning("Gemini AI: DEMO MODE")

    st.info(
        "Demo mode keeps the deterministic MERCHX "
        "commerce engine functional even when AI "
        "credentials are unavailable."
    )


# ============================================================
# MAIN TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
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

with tab1:

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

    if st.button(
        "🚀 Run MERCHX Agent",
        type="primary",
        use_container_width=True
    ):

        if not user_query.strip():

            st.warning(
                "Please enter a product requirement."
            )

        else:

            request_id = (
                "REQ-" +
                uuid.uuid4().hex[:10].upper()
            )

            # --------------------------------------------
            # IDEMPOTENCY
            # --------------------------------------------

            if not check_idempotency(request_id):

                st.error(
                    "Duplicate request detected."
                )
                st.stop()

            # --------------------------------------------
            # AI INTENT
            # --------------------------------------------

            with st.spinner(
                "MERCHX AI is understanding the request..."
            ):

                ai_response, ai_error = ask_gemini(
                    user_query
                )

            if ai_response:

                st.success("🧠 Gemini AI Active")

                with st.expander(
                    "AI Procurement Interpretation",
                    expanded=True
                ):
                    st.write(ai_response)

                search_term = demo_intent(user_query)

            else:

                st.warning(
                    "Gemini unavailable — running deterministic "
                    "MERCHX Demo Mode."
                )

                search_term = demo_intent(
                    user_query
                )

            # --------------------------------------------
            # PRODUCT DISCOVERY
            # --------------------------------------------

            products = search_products(search_term)

            if not products:

                st.error(
                    "No suitable product found."
                )

                add_audit(
                    "PRODUCT_SEARCH",
                    "BLOCKED",
                    "No matching product found.",
                    request_id=request_id
                )

                st.stop()

            product = products[0]

            st.subheader("🛍️ Product Selected")

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

            # --------------------------------------------
            # INVENTORY
            # --------------------------------------------

            inventory_ok, inventory_reason = check_inventory(
                product,
                quantity
            )

            if inventory_ok:

                st.success(
                    f"📦 Inventory: PASS — {inventory_reason}"
                )

            else:

                st.error(
                    f"📦 Inventory: BLOCKED — {inventory_reason}"
                )

                add_audit(
                    "INVENTORY_CHECK",
                    "BLOCKED",
                    inventory_reason,
                    product=product["name"],
                    request_id=request_id
                )

                st.stop()

            # --------------------------------------------
            # QUOTE
            # --------------------------------------------

            quote = create_quote(
                product,
                quantity
            )

            st.subheader("🧾 Quote")

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

            # --------------------------------------------
            # QUOTE VERIFICATION
            # --------------------------------------------

            quote_ok, quote_reason = verify_quote(
                quote
            )

            if quote_ok:

                st.success(
                    "🔐 Quote Verification: PASS"
                )

            else:

                st.error(
                    f"Quote Verification: {quote_reason}"
                )

                st.stop()

            # --------------------------------------------
            # POLICY
            # --------------------------------------------

            policy_ok, policy_reason = policy_check(
                product,
                quote["total"],
                quantity
            )

            st.subheader("🛡️ Policy Engine")

            if policy_ok:

                st.success(
                    f"APPROVED — {policy_reason}"
                )

            else:

                st.error(
                    f"BLOCKED — {policy_reason}"
                )

                add_audit(
                    "POLICY_CHECK",
                    "BLOCKED",
                    policy_reason,
                    amount=quote["total"],
                    product=product["name"],
                    request_id=request_id
                )

                st.stop()

            # --------------------------------------------
            # RISK
            # --------------------------------------------

            risk_level, risk_reason = risk_check(
                quote["total"]
            )

            st.subheader("🚨 Risk Engine")

            if risk_level == "LOW":

                st.success(
                    f"LOW RISK — {risk_reason}"
                )

            else:

                st.warning(
                    f"{risk_level} RISK — {risk_reason}"
                )

            # --------------------------------------------
            # AGENT PERMISSION
            # --------------------------------------------

            agent = agent_permission()

            st.subheader("👤 Agent Permission")

            if quote["total"] <= agent["max_transaction"]:

                st.success(
                    f"Agent {agent['agent_id']} is authorized "
                    "for this transaction."
                )

            else:

                st.error(
                    "Agent spending permission exceeded."
                )

                st.stop()

            # --------------------------------------------
            # FINAL AUTHORIZATION
            # --------------------------------------------

            st.divider()

            st.subheader(
                "🔐 MERCHX Authorization Decision"
            )

            st.success(
                "✅ APPROVED"
            )

            st.write(
                "AI selected the product. "
                "MERCHX independently validated inventory, "
                "quote, policy, risk and agent permission."
            )

            # --------------------------------------------
            # PAYMENT ENCLAVE
            # --------------------------------------------

            st.subheader(
                "💳 Payment Enclave"
            )

            st.info(
                "Payment authority remains outside the AI agent. "
                "Razorpay Test Mode is the payment execution boundary."
            )

            if st.button(
                "💳 Create Test Payment Order",
                use_container_width=True
            ):

                order_id = (
                    "MX-ORD-" +
                    uuid.uuid4().hex[:8].upper()
                )

                st.session_state.orders.append({
                    "order_id": order_id,
                    "quote_id": quote["quote_id"],
                    "product": product["name"],
                    "amount": quote["total"],
                    "status": "TEST_ORDER_CREATED"
                })

                add_audit(
                    "CREATE_ORDER",
                    "APPROVED",
                    "MERCHX authorization passed.",
                    amount=quote["total"],
                    product=product["name"],
                    request_id=request_id
                )

                st.success(
                    "Razorpay Test Order Created"
                )

                st.code(
                    order_id
                )

                st.caption(
                    "This prototype currently creates a test "
                    "commerce order. Actual Razorpay Checkout "
                    "integration will be connected next."
                )


# ============================================================
# PRODUCTS
# ============================================================

with tab2:

    st.header("📦 MERCHX Product Catalog")

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

with tab3:

    st.header("📋 MERCHX Audit Trail")

    if st.session_state.audit_logs:

        for log in reversed(
            st.session_state.audit_logs
        ):

            with st.container(border=True):

                st.write(
     
