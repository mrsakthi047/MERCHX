
import os
import re
import streamlit as st

from agent_engine import detect_intent, get_agent_response
from agent_context import AgentMemory, plan_next_step
from commerce_engine import PRODUCTS, search_products, check_inventory, get_product
from policy_engine import evaluate_policy
from risk_engine import calculate_risk, format_risk_report
from explainability_engine import explain_decision, format_explanation
from audit_engine import AuditEngine
from simulation_engine import simulate_transaction, format_simulation_report
from policy_optimizer import PolicyOptimizer
from shopping_agent import shopping_agent


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MERCHX — AI Shopping Agent",
    page_icon="🛡️",
    layout="wide",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        color: #8b949e;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }

    .agent-card {
        padding: 1rem;
        border: 1px solid rgba(128,128,128,.25);
        border-radius: 14px;
        margin-bottom: 1rem;
    }

    .small-muted {
        color: #8b949e;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API KEY
# ============================================================

def get_api_key():
    key = os.getenv("GEMINI_API_KEY")

    if key:
        return key

    try:
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


GEMINI_API_KEY = get_api_key()


# ============================================================
# SESSION STATE
# ============================================================

if "memory" not in st.session_state:
    st.session_state.memory = AgentMemory()

if "audit_engine" not in st.session_state:
    st.session_state.audit_engine = AuditEngine()

if "policy_optimizer" not in st.session_state:
    st.session_state.policy_optimizer = PolicyOptimizer()

if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

if "spent_today" not in st.session_state:
    st.session_state.spent_today = 0

if "pending_purchase" not in st.session_state:
    st.session_state.pending_purchase = None

if "web_results" not in st.session_state:
    st.session_state.web_results = None


# ============================================================
# URL EXTRACTION
# ============================================================

def extract_urls(text):
    if not text:
        return []

    urls = re.findall(
        r"https?://[^\s)\]}>\"']+",
        text
    )

    cleaned = []

    for url in urls:
        url = url.rstrip(".,;:)")

        if url not in cleaned:
            cleaned.append(url)

    return cleaned


# ============================================================
# LOCAL CATALOG SEARCH
# ============================================================

def search_local_catalog(query, max_price=None):
    return search_products(
        query=query,
        max_price=max_price
    )


# ============================================================
# PRODUCT DISPLAY
# ============================================================

def render_product(product):

    st.markdown(f"### 🛍️ {product['name']}")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**Category:** {product['category']}")

    with col2:
        st.write(f"**Price:** ₹{product['price']:,}")

    with col3:
        st.write(f"**Stock:** {product['stock']}")

    st.write(
        "**Features:** "
        + ", ".join(product["features"])
    )

    product_name = product["name"]

    search_query = product_name.replace(" ", "+")

    amazon_url = (
        "https://www.amazon.in/s?k="
        + search_query
    )

    flipkart_url = (
        "https://www.flipkart.com/search?q="
        + search_query
    )

    meesho_url = (
        "https://www.meesho.com/search?q="
        + search_query
    )

    myntra_url = (
        "https://www.myntra.com/"
        + product_name.replace(" ", "-")
    )

    st.markdown("**Search this product:**")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.link_button(
            "Amazon India",
            amazon_url,
            use_container_width=True
        )

    with c2:
        st.link_button(
            "Flipkart",
            flipkart_url,
            use_container_width=True
        )

    with c3:
        st.link_button(
            "Meesho",
            meesho_url,
            use_container_width=True
        )

    with c4:
        st.link_button(
            "Myntra",
            myntra_url,
            use_container_width=True
        )

    st.divider()


# ============================================================
# WEB RESULT DISPLAY
# ============================================================

def render_web_result(result):

    st.markdown("## 🧠 MERCHX Shopping Intelligence")

    if not result:
        return

    if not result.get("success"):
        st.error(
            result.get(
                "error",
                "Shopping agent failed."
            )
        )
        return

    text = result.get("text", "")

    if text:
        st.markdown(text)

    sources = result.get("sources", [])

    if sources:

        st.markdown("### 🔗 Discovered Web Sources")

        for index, url in enumerate(
            sources,
            start=1
        ):

            st.link_button(
                f"Open Source {index}",
                url,
                use_container_width=True
            )


# ============================================================
# PURCHASE PIPELINE
# ============================================================

def run_purchase_pipeline(
    product_id,
    quantity,
    budget
):

    product = get_product(product_id)

    if product is None:

        st.error(
            "Product not found."
        )

        return

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    inventory = check_inventory(
        product_id,
        quantity
    )

    if not inventory["available"]:

        st.error(
            "Inventory check failed."
        )

        st.write(
            "Available stock:",
            inventory.get(
                "available_stock",
                0
            )
        )

        return

    # --------------------------------------------------------
    # POLICY
    # --------------------------------------------------------

    policy = evaluate_policy(
        product=product,
        quantity=quantity,
        budget=budget,
        spent_today=st.session_state.spent_today
    )

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    try:

        risk = calculate_risk(
            product=product,
            quantity=quantity,
            policy_result=policy
        )

    except TypeError:

        risk = calculate_risk(
            product,
            quantity,
            policy
        )

    # --------------------------------------------------------
    # EXPLAINABILITY
    # --------------------------------------------------------

    try:

        explanation = explain_decision(
            product=product,
            quantity=quantity,
            policy_result=policy,
            risk_result=risk
        )

    except TypeError:

        explanation = explain_decision(
            product,
            quantity,
            policy,
            risk
        )

    # --------------------------------------------------------
    # SIMULATION
    # --------------------------------------------------------

    try:

        simulation = simulate_transaction(
            product=product,
            quantity=quantity,
            policy_result=policy,
            risk_result=risk
        )

    except TypeError:

        simulation = simulate_transaction(
            product,
            quantity,
            policy,
            risk
        )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    st.session_state.audit_engine.record(
        event_type="PURCHASE_EVALUATED",
        data={
            "product_id": product_id,
            "quantity": quantity,
            "total": policy["total"],
            "policy_approved": policy["approved"]
        }
    )

    # --------------------------------------------------------
    # DECISION UI
    # --------------------------------------------------------

    st.markdown(
        "## 🧾 MERCHX Authorization Decision"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Total",
            f"₹{policy['total']:,}"
        )

    with c2:

        st.metric(
            "Policy",
            "APPROVED"
            if policy["approved"]
            else "BLOCKED"
        )

    with c3:

        risk_score = risk.get(
            "risk_score",
            risk.get("score", 0)
        )

        st.metric(
            "Risk Score",
            str(risk_score)
        )

    if policy["approved"]:

        st.success(
            "All MERCHX policy checks passed."
        )

    else:

        st.error(
            "MERCHX blocked this transaction."
        )

        for reason in policy.get(
            "reasons",
            []
        ):

            st.warning(reason)

    # --------------------------------------------------------
    # DETAILS
    # --------------------------------------------------------

    with st.expander(
        "🔎 View Decision Details",
        expanded=True
    ):

        st.markdown(
            "### 🛡️ Policy Checks"
        )

        st.json(
            policy.get(
                "checks",
                {}
            )
        )

        st.markdown(
            "### ⚠️ Risk Analysis"
        )

        try:

            st.markdown(
                format_risk_report(risk)
            )

        except Exception:

            st.json(risk)

        st.markdown(
            "### 💡 Explainability"
        )

        try:

            st.markdown(
                format_explanation(
                    explanation
                )
            )

        except Exception:

            st.write(explanation)

        st.markdown(
            "### 🧪 Transaction Simulation"
        )

        try:

            st.markdown(
                format_simulation_report(
                    simulation
                )
            )

        except Exception:

            st.write(simulation)

    # --------------------------------------------------------
    # APPROVAL
    # --------------------------------------------------------

    if policy["approved"]:

        st.session_state.pending_purchase = {
            "product_id": product_id,
            "quantity": quantity,
            "total": policy["total"]
        }

        st.info(
            "MERCHX authorization passed. "
            "Human approval is required before "
            "payment simulation."
        )

    else:

        failed_checks = [
            key
            for key, value in policy.get(
                "checks",
                {}
            ).items()
            if value == "FAIL"
        ]

        if failed_checks == [
            "transaction_limit"
        ]:

            st.warning(
                "Transaction limit exceeded. "
                "Human-in-the-Loop escalation is available."
            )

            st.session_state.pending_purchase = {
                "product_id": product_id,
                "quantity": quantity,
                "total": policy["total"]
            }


# ============================================================
# HUMAN APPROVAL
# ============================================================

def approve_pending_purchase():

    pending = (
        st.session_state.pending_purchase
    )

    if not pending:
        return

    product = get_product(
        pending["product_id"]
    )

    if product is None:

        st.error(
            "Pending product no longer exists."
        )

        st.session_state.pending_purchase = None

        return

    total = pending["total"]

    # --------------------------------------------------------
    # AUDIT: HUMAN APPROVAL
    # --------------------------------------------------------

    st.session_state.audit_engine.record(
        event_type="HUMAN_APPROVAL",
        data={
            "product_id": pending["product_id"],
            "quantity": pending["quantity"],
            "total": total
        }
    )

    # --------------------------------------------------------
    # SIMULATED PAYMENT
    # --------------------------------------------------------

    st.session_state.audit_engine.record(
        event_type="PAYMENT_SIMULATED",
        data={
            "product_id": pending["product_id"],
            "quantity": pending["quantity"],
            "total": total,
            "payment_rail": "Razorpay Test Mode / Simulation"
        }
    )

    # --------------------------------------------------------
    # SPEND
    # --------------------------------------------------------

    st.session_state.spent_today += total

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    st.session_state.memory.log(
        "purchase",
        {
            "product_id": pending["product_id"],
            "quantity": pending["quantity"],
            "total": total
        }
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    st.success(
        "Human approval received."
    )

    st.success(
        "Payment simulation completed successfully."
    )

    st.info(
        "Demo only: no real money was charged "
        "and no real order was created."
    )

    st.session_state.pending_purchase = None


# ============================================================
# MESSAGE HANDLER
# ============================================================

def handle_message(user_input):

    user_input = user_input.strip()

    if not user_input:
        return

    # --------------------------------------------------------
    # CHAT LOG
    # --------------------------------------------------------

    st.session_state.chat_log.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    # --------------------------------------------------------
    # INTENT
    # --------------------------------------------------------

    intent = detect_intent(
        user_input
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    try:

        next_step = plan_next_step(
            intent,
            user_input,
            st.session_state.memory
        )

    except Exception:

        next_step = {
            "step": intent
        }

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    st.session_state.memory.log(
        "intent",
        {
            "input": user_input,
            "intent": intent,
            "next_step": next_step
        }
    )

    # --------------------------------------------------------
    # LIVE SHOPPING
    # --------------------------------------------------------

    shopping_keywords = [
        "buy",
        "find",
        "search",
        "best",
        "cheap",
        "price",
        "compare",
        "laptop",
        "phone",
        "headphone",
        "headphones",
        "watch",
        "keyboard",
        "shoes",
        "shirt",
        "amazon",
        "flipkart",
        "meesho",
        "myntra"
    ]

    wants_web = any(
        word in user_input.lower()
        for word in shopping_keywords
    )

    if wants_web and GEMINI_API_KEY:

        result = shopping_agent(
            user_input
        )

        if result.get("success"):

            st.session_state.web_results = result

            st.session_state.chat_log.append(
                {
                    "role": "assistant",
                    "content": result.get(
                        "text",
                        "Live shopping research completed."
                    )
                }
            )

            return

        st.session_state.chat_log.append(
            {
                "role": "assistant",
                "content": (
                    "Shopping Agent error: "
                    + result.get(
                        "error",
                        "Unknown error"
                    )
                )
            }
        )

        return

    # --------------------------------------------------------
    # LOCAL SEARCH
    # --------------------------------------------------------

    if intent == "SEARCH":

        results = search_local_catalog(
            user_input
        )

        if results:

            st.session_state.memory.remember_search(
                results
            )

            st.session_state.chat_log.append(
                {
                    "role": "assistant",
                    "content": (
                        f"Found {len(results)} "
                        "MERCHX catalog result(s)."
                    )
                }
            )

        else:

            st.session_state.chat_log.append(
                {
                    "role": "assistant",
                    "content": (
                        "No local catalog match. "
                        "Add GEMINI_API_KEY to enable "
                        "live shopping intelligence."
                    )
                }
            )

        return

    # --------------------------------------------------------
    # DEFAULT AGENT RESPONSE
    # --------------------------------------------------------

    st.session_state.chat_log.append(
        {
            "role": "assistant",
            "content": get_agent_response(
                intent
            )
        }
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🛡️ MERCHX</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-Native Shopping Intelligence & Commerce Protocol'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# TOP STATUS
# ============================================================

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "Protocol",
        "ONLINE"
    )

with c2:

    st.metric(
        "Gemini",
        "CONNECTED"
        if GEMINI_API_KEY
        else "OFFLINE"
    )

with c3:

    st.metric(
        "Spent Today",
        f"₹{st.session_state.spent_today:,}"
    )

with c4:

    st.metric(
        "Audit Events",
        len(
            st.session_state.audit_engine.events
        )
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "⚙️ MERCHX Control Center"
    )

    st.markdown(
        "### 🧠 Agent Stack"
    )

    st.write(
        "• Intent Engine"
    )
