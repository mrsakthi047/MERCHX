# ============================================================
# MERCHX — AI-NATIVE SHOPPING INTELLIGENCE & COMMERCE PROTOCOL
# ============================================================

import os
import re
import json
import streamlit as st

from google import genai
from google.genai import types

from agent_engine import (
    detect_intent,
    requires_confirmation,
    get_agent_response,
)

from agent_context import AgentMemory, plan_next_step

from commerce_engine import (
    search_products,
    check_inventory,
    get_product,
)

from policy_engine import evaluate_policy

from risk_engine import (
    calculate_risk,
    format_risk_report,
)

from explainability_engine import (
    explain_decision,
    format_explanation,
)

from audit_engine import AuditEngine

from simulation_engine import (
    simulate_transaction,
    format_simulation_report,
)

from policy_optimizer import PolicyOptimizer

from shopping_agent import (
    shopping_agent,
    shopping_agent_status,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="MERCHX — AI Shopping Agent",
    page_icon="🛡️",
    layout="wide",
)


# ============================================================
# PREMIUM UI
# ============================================================

st.markdown(
    """
<style>

.main-title {
    font-size: 3rem;
    font-weight: 800;
    letter-spacing: -2px;
    margin-bottom: 0.2rem;
}

.subtitle {
    color: #8b949e;
    font-size: 1.05rem;
    margin-bottom: 1.5rem;
}

.agent-card {
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 18px;
    padding: 22px;
    background: rgba(255,255,255,0.025);
    margin-bottom: 15px;
}

.score {
    font-size: 2rem;
    font-weight: 800;
}

.status-online {
    font-weight: 700;
}

.product-card {
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 18px;
    margin: 10px 0;
    background: rgba(255,255,255,0.025);
}

.small-muted {
    color: #8b949e;
    font-size: 0.85rem;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🛡️ MERCHX</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'AI-Native Shopping Intelligence & Commerce Protocol'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    try:
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        GEMINI_API_KEY = ""

client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        client = None


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
# HELPERS
# ============================================================

def extract_urls(text):
    """Extract URLs from research output."""

    if not text:
        return []

    urls = re.findall(
        r"https?://[^\s)\]}>\"']+",
        text,
    )

    cleaned = []

    for url in urls:
        url = url.rstrip(".,;:)")

        if url not in cleaned:
            cleaned.append(url)

    return cleaned


def safe_json(data):
    """Pretty JSON for UI."""

    try:
        return json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    except Exception:
        return str(data)


# ============================================================
# LOCAL CATALOG SEARCH
# ============================================================

def local_catalog_search(query):
    """Search MERCHX internal catalog."""

    try:
        return search_products(query)
    except Exception:
        return []


# ============================================================
# LIVE SHOPPING AGENT
# ============================================================

def run_live_shopping_agent(user_request):

    if not GEMINI_API_KEY:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is not configured.",
            "text": "",
            "sources": [],
            "products": [],
        }

    result = shopping_agent(user_request)

    return result


# ============================================================
# DISPLAY LIVE WEB RESULT
# ============================================================

def display_web_result(result):

    if not result:
        return

    if not result.get("success"):

        st.error(
            "Shopping Agent Error: "
            + str(result.get("error", "Unknown error"))
        )

        return

    text = result.get("text", "")
    sources = result.get("sources", [])

    if text:

        st.markdown("### 🧠 MERCHX Shopping Intelligence")

        st.markdown(text)

    if sources:

        st.markdown("### 🔗 Verified Web Sources")

        for index, url in enumerate(sources, start=1):

            st.markdown(
                f"[{index}. Open verified source]({url})"
            )


# ============================================================
# LOCAL PRODUCT DISPLAY
# ============================================================

def show_products(products):

    if not products:

        st.info(
            "No matching products found in the MERCHX internal catalog."
        )

        return

    st.markdown("### 🛍️ MERCHX Catalog")

    for product in products:

        st.markdown(
            f"""
<div class="product-card">

<h3>{product["name"]}</h3>

<p>
<b>ID:</b> {product["id"]}<br>
<b>Category:</b> {product["category"]}<br>
<b>Price:</b> ₹{product["price"]:,}<br>
<b>Stock:</b> {product["stock"]}
</p>

<p>
<b>Features:</b>
{", ".join(product["features"])}
</p>

</div>
""",
            unsafe_allow_html=True,
        )

        query = product["name"].replace(" ", "+")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f"[🛒 Amazon Search](https://www.amazon.in/s?k={query})"
            )

        with col2:
            st.markdown(
                f"[🛒 Flipkart Search](https://www.flipkart.com/search?q={query})"
            )

        with col3:
            st.markdown(
                f"[🛒 Meesho Search](https://www.meesho.com/search?q={query})"
            )

        with col4:
            st.markdown(
                f"[🛒 Myntra Search](https://www.myntra.com/{query})"
            )


# ============================================================
# PURCHASE PIPELINE
# ============================================================

def purchase_pipeline(
    product_id,
    quantity=1,
    budget=None,
):

    product = get_product(product_id)

    if product is None:

        st.error("Product not found.")

        return None

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    inventory = check_inventory(
        product_id,
        quantity,
    )

    st.markdown("### 📦 Inventory Check")

    if inventory["available"]:

        st.success(
            f"Inventory PASS — {inventory['available_stock']} "
            f"units available."
        )

    else:

        st.error(
            f"Inventory FAIL — requested {quantity}, "
            f"available {inventory['available_stock']}."
        )

        return None

    # --------------------------------------------------------
    # POLICY
    # --------------------------------------------------------

    policy = evaluate_policy(
        product=product,
        quantity=quantity,
        budget=budget,
        spent_today=st.session_state.spent_today,
    )

    st.markdown("### 🛡️ Policy Engine")

    if policy["approved"]:
        st.success("Policy Engine: APPROVED")
    else:

        st.error("Policy Engine: BLOCKED")

        for reason in policy["reasons"]:
            st.warning(reason)

    # --------------------------------------------------------
    # RISK
    # --------------------------------------------------------

    risk = calculate_risk(
        product=product,
        quantity=quantity,
        total=policy["total"],
    )

    st.markdown("### ⚠️ Risk Engine")

    st.markdown(
        format_risk_report(risk)
    )

    # --------------------------------------------------------
    # HARD BLOCKS
    # --------------------------------------------------------

    hard_block = any(
        value == "FAIL"
        for key, value in policy["checks"].items()
        if key != "transaction_limit"
    )

    if hard_block:

        st.error(
            "Transaction blocked because one or more mandatory "
            "policy controls failed."
        )

        st.session_state.audit_engine.record(
            event_type="TRANSACTION_BLOCKED",
            data={
                "product_id": product_id,
                "quantity": quantity,
                "policy": policy,
                "risk": risk,
            },
        )

        return None

    # --------------------------------------------------------
    # HUMAN APPROVAL
    # --------------------------------------------------------

    requires_human = (
        not policy["approved"]
        or risk.get("risk_level", "").upper()
        in ["HIGH", "CRITICAL"]
    )

    if requires_human:

        st.warning(
            "🧑‍💻 Human approval required before payment."
        )

        approval_key = (
            f"approve_{product_id}_{quantity}"
        )

        approved = st.checkbox(
            "I approve this transaction",
            key=approval_key,
        )

        if not approved:

            st.info(
                "Waiting for human approval."
            )

            st.session_state.pending_purchase = {
                "product_id": product_id,
                "quantity": quantity,
                "total": policy["total"],
            }

            return None

    # --------------------------------------------------------
    # SIMULATION
    # --------------------------------------------------------

    simulation = simulate_transaction(
        product=product,
        quantity=quantity,
        total=policy["total"],
    )

    st.markdown("### 🧪 Transaction Simulation")

    st.markdown(
        format_simulation_report(simulation)
    )

    # --------------------------------------------------------
    # EXPLAINABILITY
    # --------------------------------------------------------

    explanation = explain_decision(
        product=product,
        policy=policy,
        risk=risk,
        simulation=simulation,
    )

    st.markdown("### 🧠 Decision Explainability")

    st.markdown(
        format_explanation(explanation)
    )

    # --------------------------------------------------------
    # AUDIT
    # --------------------------------------------------------

    audit_data = {
        "product_id": product_id,
        "product_name": product["name"],
        "quantity": quantity,
        "total": policy["total"],
        "policy": policy,
        "risk": risk,
        "simulation": simulation,
    }

    st.session_state.audit_engine.record(
        event_type="TRANSACTION_AUTHORIZED",
        data=audit_data,
    )

    # --------------------------------------------------------
    # SIMULATED PAYMENT
    # --------------------------------------------------------

    st.markdown("### 💳 Payment Layer")

    st.info(
        "Razorpay Test Mode integration point — "
        "payment execution is currently simulated."
    )

    st.success(
        "✅ MERCHX authorization completed successfully."
    )

    st.session_state.spent_today += policy["total"]

    st.session_state.pending_purchase = None

    return audit_data


# ============================================================
# MESSAGE HANDLER
# ============================================================

def handle_message(user_input):

    if not user_input:
        return

    user_input = user_input.strip()

    if not user_input:
        return

    intent = detect_intent(user_input)

    memory = st.session_state.memory

    try:
        next_step = plan_next_step(
            intent,
            user_input,
            memory,
        )
    except Exception:
        next_step = None

    memory.log(
        user_input,
        intent=intent,
    )

    st.session_state.chat_log.append(
        {
            "role": "user",
            "content": user_input,
            "intent": intent,
        }
    )

    # ========================================================
    # HELP
    # ========================================================

    if intent == "HELP":

        response = get_agent_response(intent)

        st.session_state.chat_log.append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        return

    # ========================================================
    # SHOPPING INTELLIGENCE
    # ========================================================

    shopping_keywords = [
        "buy",
        "purchase",
        "shop",
        "shopping",
        "find",
        "recommend",
        "best",
        "compare",
        "price",
        "product",
        "laptop",
        "phone",
        "headphone",
        "headphones",
        "watch",
        "keyboard",
        "shoes",
        "shirt",
        "dress",
        "amazon",
        "flipkart",
        "meesho",
        "myntra",
    ]

    should_use_web_agent = any(
        keyword in user_input.lower()
        for keyword in shopping_keywords
    )

    if should_use_web_agent:

        with st.spinner(
            "🔎 MERCHX is researching the live web..."
        ):

            result = run_live_shopping_agent(
                user_input
            )

        st.session_state.web_results = result

        if result.get("success"):

            memory.remember_search(
                user_input,
                result.get("text", ""),
            )

        return

    # ========================================================
    # LOCAL SEARCH
    # ========================================================

    if intent == "SEARCH":

        results = local_catalog_search(
            user_input
        )

        if results:

            memory.remember_search(
                user_input,
                results,
            )

            show_products(results)

        else:

            st.info(
                "No local catalog match. "
                "Try a more specific product name."
            )

        return

    # ========================================================
    # INVENTORY
    # ========================================================

    if intent == "INVENTORY":

        results = local_catalog_search(
            user_input
        )

        if results:

            for product in results:

                inventory = check_inventory(
                    product["id"]
                )

                if inventory["available"]:

                    st.success(
                        f'{product["name"]}: '
                        f'{inventory["available_stock"]} units available.'
                    )

                else:

                    st.error(
                        f'{product["name"]}: Out of stock.'
                    )

        else:

            st.info(
                "No matching product found."
            )

        return

    # ========================================================
    # QUOTE
    # ========================================================

    if intent == "QUOTE":

        results = local_catalog_search(
            user_input
        )

        if results:

            product = results[0]

            quantity = 1

            total = (
                product["price"] * quantity
            )

            st.markdown("### 🧾 MERCHX Quote")

            st.write(
                f'**Product:** {product["name"]}'
            )

            st.write(
                f'**Quantity:** {quantity}'
            )

            st.write(
                f'**Unit Price:** ₹{product["price"]:,}'
            )

            st.write(
                f'**Total:** ₹{total:,}'
            )

            memory.remember_quote(
                product,
                quantity,
                total,
            )

        else:

            st.info(
                "No matching product found."
            )

        return

    # ========================================================
    # BUY
    # ========================================================

    if intent == "BUY":

        results = local_catalog_search(
            user_input
        )

        if not results:

            st.warning(
                "I couldn't match that to a MERCHX catalog product."
            )

            return

        product = results[0]

        memory.remember_selection(
            product
        )

        purchase_pipeline(
            product_id=product["id"],
            quantity=1,
        )

        return

    # ========================================================
    # FALLBACK
    # ========================================================

    response = get_agent_response(
        intent
    )

    st.session_state.chat_log.append(
        {
            "role": "assistant",
            "content": response,
        }
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🛡️ MERCHX")

    st.caption(
        "AI-Native Commerce Protocol"
    )

    st.divider()

    st.metric(
        "Today's Spend",
        f"₹{st.session_state.spent_today:,}",
    )

    st.metric(
        "Audit Events",
        len(
            st.session_state.audit_engine.events
        ),
    )

    st.divider()

    st.markdown("### 🧠 Agent Stack")

    st.write("🧠 AI Shopping Agent")
    st.write("🔎 Live Web Research")
    st.write("📦 Inventory Engine")
    st.write("🧾 Quote Engine")
    st.write("🛡️ Policy Engine")
    st.write("⚠️ Risk Engine")
    st.write("🧑‍💻 Human Approval")
    st.write("💳 Payment Layer")
    st.write("📋 Audit Engine")

    st.divider()

    status = shopping_agent_status()

    if status["status"] == "ONLINE":

        st.success(
            "Shopping Agent: ONLINE"
        )

    else:

        st.warning(
            "Shopping Agent: OFFLINE"
        )

    st.caption(
        "Gemini API required for live web shopping."
    )

    st.divider()

    if st.button(
        "🔐 Check Audit Integrity",
        use_container_width=True,
    ):

        try:

            integrity = (
                st.session_state.audit_engine.verify_integrity()
            )

            if integrity:

                st.success(
    "Audit chain integrity verified."
)