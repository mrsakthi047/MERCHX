import os
import json
import re
import streamlit as st

from google import genai
from google.genai import types

from agent_engine import detect_intent, get_agent_response
from agent_context import AgentMemory, plan_next_step
from commerce_engine import search_products, check_inventory
from policy_engine import evaluate_policy
from risk_engine import calculate_risk, format_risk_report
from explainability_engine import explain_decision, format_explanation
from audit_engine import AuditEngine
from simulation_engine import simulate_transaction, format_simulation_report
from policy_optimizer import PolicyOptimizer


# ============================================================
# MERCHX CONFIG
# ============================================================

st.set_page_config(
    page_title="MERCHX — AI Shopping Agent",
    page_icon="🛡️",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .subtitle {
        color: #888;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .agent-card {
        padding: 18px;
        border-radius: 14px;
        border: 1px solid rgba(128,128,128,0.25);
        margin-bottom: 15px;
    }

    .score {
        font-size: 32px;
        font-weight: 800;
    }

    </style>
    """,
    unsafe_allow_html=True
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
# GEMINI CLIENT
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:

    try:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        GEMINI_API_KEY = None


if GEMINI_API_KEY:

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

else:

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
    st.session_state.web_results = []


memory = st.session_state.memory
audit_engine = st.session_state.audit_engine
policy_optimizer = st.session_state.policy_optimizer


# ============================================================
# LOCAL PRODUCT SEARCH
# ============================================================

def search_catalog(query, budget=None):

    query = query.lower().strip()

    results = search_products(
        query,
        max_price=budget
    )

    if results:
        return results

    fallback = []

    for word in query.split():

        if len(word) < 3:
            continue

        matches = search_products(
            word,
            max_price=budget
        )

        for product in matches:

            if product not in fallback:
                fallback.append(product)

    return fallback


# ============================================================
# AI WEB SHOPPING AGENT
# ============================================================

def run_web_shopping_agent(user_query):

    if not client:

        return {
            "error": (
                "Gemini API key not configured. "
                "Add GEMINI_API_KEY to Streamlit secrets."
            )
        }

    prompt = f"""
You are MERCHX, an autonomous AI shopping intelligence agent.

User request:
{user_query}

Your job is to research the web and identify REAL products.

IMPORTANT RULES:

1. Search the live web.
2. Prefer official retailer/product pages.
3. Never invent a product URL.
4. Never invent a price.
5. Never invent ratings or review counts.
6. If exact information cannot be verified, say "Not verified".
7. Compare multiple retailers where possible.
8. Find the best value option.
9. Analyse available reviews.
10. Give concise pros and cons.
11. Explain why the recommended product is best.
12. Return REAL source URLs from search results.
13. Do not claim that you purchased anything.
14. Do not claim that payment happened.

Search these marketplaces when relevant:

Amazon India
Flipkart
Myntra
Meesho

Also search other trustworthy stores if useful.

Return the answer using this structure:

PRODUCT_RESULTS

For every product include:

NAME:
BRAND:
PRICE:
RETAILER:
RATING:
REVIEW_COUNT:
PRODUCT_URL:
SOURCE_URL:
PROS:
- ...
CONS:
- ...
TRUST_SCORE:
VALUE_SCORE:

Then:

BEST_PICK:
product name

WHY:
short explanation

PRICE_COMPARISON:
retailer + price + URL

REVIEW_INTELLIGENCE:
short summary

MERCHX_RECOMMENDATION:
short recommendation

VERIFICATION:
what was verified and what was not
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ]
            )
        )

        return {
            "text": response.text
        }

    except Exception as error:

        return {
            "error": str(error)
        }


# ============================================================
# EXTRACT URLS
# ============================================================

def extract_urls(text):

    if not text:
        return []

    urls = re.findall(
        r'https?://[^\s)\]}>"]+',
        text
    )

    clean_urls = []

    for url in urls:

        url = url.rstrip(".,;")

        if url not in clean_urls:
            clean_urls.append(url)

    return clean_urls


# ============================================================
# DISPLAY WEB SHOPPING RESULT
# ============================================================

def display_web_result(result):

    if result.get("error"):

        st.error(
            f"⚠️ {result['error']}"
        )

        return

    text = result.get(
        "text",
        ""
    )

    st.markdown(
        "## 🧠 MERCHX SHOPPING INTELLIGENCE"
    )

    st.markdown(text)

    urls = extract_urls(text)

    if urls:

        st.markdown(
            "### 🔗 Verified Web Sources"
        )

        for index, url in enumerate(
            urls,
            1
        ):

            st.markdown(
                f"[🌐 Open Source {index}]({url})"
            )

    st.divider()

    st.success(
        "MERCHX completed live web research."
    )


# ============================================================
# PRODUCT DISPLAY
# ============================================================

def show_products(products):

    if not products:

        st.warning(
            "❌ No local MERCHX products found."
        )

        return

    st.markdown(
        "## 🛒 MERCHX CATALOG"
    )

    for index, product in enumerate(
        products,
        1
    ):

        st.markdown("---")

        col1, col2 = st.columns(
            [3, 1]
        )

        with col1:

            st.markdown(
                f"### {index}. {product['name']}"
            )

            st.write(
                f"💰 ₹{product['price']:,}"
            )

            st.write(
                f"📦 Stock: {product['stock']}"
            )

            st.write(
                f"🏷️ {product['category']}"
            )

            st.write(
                "⚙️ "
                + ", ".join(
                    product.get(
                        "features",
                        []
                    )
                )
            )

            st.code(
                product["id"]
            )

        with col2:

            st.markdown(
                "#### Marketplace"
            )

            query = product["name"]

            st.link_button(
                "🟠 Amazon",
                f"https://www.amazon.in/s?k={query.replace(' ', '+')}",
                use_container_width=True
            )

            st.link_button(
                "🔵 Flipkart",
                f"https://www.flipkart.com/search?q={query.replace(' ', '+')}",
                use_container_width=True
            )

            st.link_button(
                "🩷 Meesho",
                f"https://www.meesho.com/search?q={query.replace(' ', '+')}",
                use_container_width=True
            )

            st.link_button(
                "🟣 Myntra",
                f"https://www.myntra.com/search?q={query.replace(' ', '+')}",
                use_container_width=True
            )


# ============================================================
# PURCHASE PIPELINE
# ============================================================

def purchase_pipeline(
    product,
    quantity=1,
    budget=None
):

    total = product["price"] * quantity

    spent_today = (
        st.session_state.spent_today
    )

    inventory = check_inventory(
        product["id"],
        quantity
    )

    if not inventory["available"]:

        event = audit_engine.record_event(
            action="PURCHASE_BLOCKED",
            agent_id="AGENT-001",
            product_id=product["id"],
            amount=total,
            decision="BLOCKED",
            risk_level="HIGH",
            policy_status="INVENTORY_FAIL",
            payment_status="NOT_EXECUTED"
        )

        return (
            "🚫 **PURCHASE BLOCKED**\n\n"
            f"Product: {product['name']}\n"
            f"Requested: {quantity}\n"
            f"Available: "
            f"{inventory['available_stock']}\n\n"
            f"📋 Audit ID: "
            f"`{event['audit_id']}`"
        )

    policy = evaluate_policy(
        product=product,
        quantity=quantity,
        budget=budget,
        spent_today=spent_today
    )

    hard_failures = []

    for key, status in policy["checks"].items():

        if (
            status == "FAIL"
            and key != "transaction_limit"
        ):

            hard_failures.append(key)

    transaction_limit_review = (
        policy["checks"]["transaction_limit"]
        == "FAIL"
        and not hard_failures
    )

    risk = calculate_risk(
        amount=total,
        quantity=quantity,
        stock=product["stock"],
        vendor_trusted=True,
        agent_verified=True,
        transaction_count=len(
            audit_engine.get_events()
        ),
        policy_violation=bool(
            hard_failures
        )
    )

    simulation = simulate_transaction(
        product=product,
        quantity=quantity,
        budget=budget,
        risk_result=risk,
        policy_result=policy,
        vendor_trusted=True
    )

    if hard_failures:

        decision = "BLOCKED"

    elif risk["level"] == "HIGH":

        decision = "BLOCKED"

    elif (
        transaction_limit_review
        or risk["level"] == "MEDIUM"
        or simulation["recommendation"]
        == "HUMAN_REVIEW"
    ):

        decision = (
            "HUMAN_APPROVAL_REQUIRED"
        )

    else:

        decision = "APPROVED"

    explanation = explain_decision(
        decision=decision,
        risk_result=risk,
        policy_result=policy,
        product=product,
        quantity=quantity,
        total_amount=total
    )

    if decision == "BLOCKED":

        event = audit_engine.record_event(
            action="PURCHASE_BLOCKED",
            agent_id="AGENT-001",
            product_id=product["id"],
            amount=total,
            decision="BLOCKED",
            risk_level=risk["level"],
            policy_status="BLOCKED",
            payment_status="NOT_EXECUTED",
            metadata={
                "policy_reasons": policy[
                    "reasons"
                ],
                "hard_failures":
                    hard_failures
            }
        )

        return (
            "🚫 **MERCHX TRANSACTION BLOCKED**\n\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"{format_risk_report(risk)}\n\n"
            f"{format_explanation(explanation)}\n\n"
            f"📋 Audit ID: "
            f"`{event['audit_id']}`"
        )

    if decision == "HUMAN_APPROVAL_REQUIRED":

        st.session_state.pending_purchase = {

            "product": product,

            "quantity": quantity,

            "budget": budget,

            "total": total,

            "policy": policy,

            "risk": risk,

            "simulation": simulation,

            "explanation": explanation
        }

        return (
            "🟡 **HUMAN APPROVAL REQUIRED**\n\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"{format_risk_report(risk)}\n\n"
            f"{format_simulation_report(simulation)}\n\n"
            f"{format_explanation(explanation)}"
        )

    event = audit_engine.record_event(
        action="PURCHASE_APPROVED",
        agent_id="AGENT-001",
        product_id=product["id"],
        amount=total,
        decision="APPROVED",
        risk_level=risk["level"],
        policy_status="APPROVED",
        payment_status="SIMULATED_SUCCESS"
    )

    st.session_state.spent_today += total

    return (
        "✅ **MERCHX TRANSACTION APPROVED**\n\n"
        f"Product: {product['name']}\n"
        f"Quantity: {quantity}\n"
        f"Total: ₹{total:,}\n\n"
        f"{format_risk_report(risk)}\n\n"
        f"{format_explanation(explanation)}\n\n"
        "💳 Payment: **SIMULATED SUCCESS**\n"
        "📦 Order: **CREATED**\n"
        f"📋 Audit ID: "
        f"`{event['audit_id']}`"
    )


# ============================================================
# AI AGENT HANDLER
# ============================================================

def handle_message(user_input):

    intent = detect_intent(
        user_input
    )

    step = plan_next_step(
        intent,
        user_input,
        memory
    )

    memory.log(
        user_input,
        intent,
        step
    )

    action = step["action"]

    payload = step["payload"]

    # --------------------------------------------------------
    # AI WEB SHOPPING
    # --------------------------------------------------------

    shopping_keywords = [
        "find",
        "search",
        "best",
        "cheapest",
        "price",
        "compare",
        "buy",
        "shop",
        "recommend",
        "reviews",
        "review",
        "amazon",
        "flipkart",
        "myntra",
        "meesho"
    ]

    if any(
        word in user_input.lower()
        for word in shopping_keywords
    ):

        result = run_web_shopping_agent(
            user_input
        )

        return {
            "type": "WEB",
            "data": result
        }

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if action == "HELP":

        return get_agent_response(
            "HELP"
        )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if action == "SEARCH":

        if "keyword" in payload:

            keyword = payload["keyword"]

            budget = payload.get(
                "budget"
            )

            results = search_catalog(
                keyword,
                budget
            )

            memory.remember_search(
                results,
                budget,
                payload.get("quantity")
            )

            return {
                "type": "LOCAL",
                "data": results
            }

    # --------------------------------------------------------
    # BUY
    # --------------------------------------------------------

    if action == "RUN_PURCHASE_PIPELINE":

        product = payload["product"]

        quantity = payload.get(
            "quantity",
            1
        )

        budget = memory.budget_hint

        return {
            "type": "TEXT",
            "data": purchase_pipeline(
                product,
                quantity,
                budget
            )
        }

    return {
        "type": "TEXT",
        "data": get_agent_response(
            intent
        )
    }


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header(
        "🛡️ MERCHX CONTROL"
    )

    st.metric(
        "Today's Spend",
        f"₹{st.session_state.spent_today:,}"
    )

    st.metric(
        "Audit Events",
        len(
            audit_engine.get_events()
        )
    )

    st.divider()

    st.subheader(
        "🤖 Agent Stack"
    )

    st.write(
        "🧠 Intent Agent"
    )

    st.write(
        "🔎 Discovery Agent"
    )

    st.write(
        "💰 Price Intelligence"
    )

    st.write(
        "⭐ Review Intelligence"
    )

    st.write(
        "🏆 Recommendation Agent"
    )

    st.write(
        "⚖️ Policy Engine"
    )

    st.write(
        "🛡️ Risk Engine"
    )

    st.write(
        "👤 Human-in-the-Loop"
    )

    st.write(
        "📋 Audit Engine"
    )

    st.divider()

    st.subheader(
        "⚡ Protocol Status"
    )

    st.success(
        "Agent Online"
    )

    st.success(
        "Policy Engine Active"
    )

    st.success(
        "Risk Engine Active"
    )

    st.success(
        "Audit Engine Active"
    )

    if client:

        st.success(
            "🌐 Web Intelligence Online"
        )

    else:

        st.warning(
            "🌐 Web Intelligence Offline"
        )

    st.divider()

    if st.button(
        "🔍 Verify Audit Integrity",
        use_container_width=True
    ):

        if audit_engine.verify_integrity():

            st.success(
                "Audit chain integrity verified."
            )

        else:

            st.error(
                "Audit chain integrity failed."
            )

    if st.button(
        "🧹 Clear Chat",
        use_container_width=True
    ):

        st.session_state.chat_log = []

        st.session_state.memory = (
            AgentMemory()
        )

        st.session_state.pending_purchase = None

        st.rerun()


# ============================================================
# HUMAN APPROVAL PANEL
# ============================================================

pending = (
    st.session_state.pending_purchase
)

if pending:

    st.warning(
        "🟡 HUMAN-IN-THE-LOOP APPROVAL"
    )

    product = pending["product"]

    risk = pending["risk"]

    st.write(
        f"**Product:** {product['name']}"
    )

    st.write(
        f"**Quantity:** {pending['quantity']}"
    )

    st.write(
        f"**Total:** ₹{pending['total']:,}"
    )

    st.write(
        f"**Risk:** "
        f"{risk['level']} — "
        f"{risk['score']}/100"
    )

    with st.expander(
        "🔎 View Decision Details"
    ):

        st.markdown(
            format_risk_report(risk)
        )

        st.markdown(
            format