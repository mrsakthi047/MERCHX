import streamlit as st
from urllib.parse import quote_plus

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
    page_title="MERCHX",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ MERCHX")
st.caption("AI-Native Commerce Protocol")


# ============================================================
# MARKETPLACE LINK ENGINE
# ============================================================

def marketplace_links(product_name):
    """
    Generate clickable marketplace search links.

    These links search for the exact MERCHX product name
    on each marketplace instead of inventing a fake product URL.
    """

    query = quote_plus(product_name)

    return {
        "Amazon": f"https://www.amazon.in/s?k={query}",
        "Flipkart": f"https://www.flipkart.com/search?q={query}",
        "Meesho": f"https://www.meesho.com/search?q={query}",
        "Myntra": f"https://www.myntra.com/search?q={query}",
    }


def render_marketplace_links(product_name):
    """
    Render clickable marketplace buttons/links.
    """

    links = marketplace_links(product_name)

    st.markdown("### 🛍️ Shop on Marketplace")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"[🟠 **Amazon**]({links['Amazon']})"
        )

    with col2:
        st.markdown(
            f"[🔵 **Flipkart**]({links['Flipkart']})"
        )

    with col3:
        st.markdown(
            f"[🩷 **Meesho**]({links['Meesho']})"
        )

    with col4:
        st.markdown(
            f"[🟣 **Myntra**]({links['Myntra']})"
        )


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


memory = st.session_state.memory
audit_engine = st.session_state.audit_engine
policy_optimizer = st.session_state.policy_optimizer


# ============================================================
# PRODUCT SEARCH
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
# PRODUCT DISPLAY
# ============================================================

def show_products(products):

    if not products:
        st.error("❌ No matching products found.")
        return

    st.markdown("## 🛒 MERCHX PRODUCT DISCOVERY")

    for index, product in enumerate(products, 1):

        st.markdown("---")

        st.markdown(
            f"### {index}. {product['name']}"
        )

        col1, col2 = st.columns([2, 1])

        with col1:

            st.markdown(
                f"💰 **Price:** ₹{product['price']:,}"
            )

            st.markdown(
                f"📦 **Stock:** {product['stock']}"
            )

            st.markdown(
                f"🏷️ **Category:** {product['category']}"
            )

            st.markdown(
                f"⚙️ **Features:** "
                f"{', '.join(product.get('features', []))}"
            )

            st.markdown(
                f"🆔 **Product ID:** `{product['id']}`"
            )

        with col2:

            st.markdown("#### 🛍️ Marketplace")

            links = marketplace_links(
                product["name"]
            )

            st.link_button(
                "🟠 Amazon",
                links["Amazon"],
                use_container_width=True
            )

            st.link_button(
                "🔵 Flipkart",
                links["Flipkart"],
                use_container_width=True
            )

            st.link_button(
                "🩷 Meesho",
                links["Meesho"],
                use_container_width=True
            )

            st.link_button(
                "🟣 Myntra",
                links["Myntra"],
                use_container_width=True
            )

    st.markdown("---")


# ============================================================
# PURCHASE PIPELINE
# ============================================================

def purchase_pipeline(product, quantity=1, budget=None):

    total = product["price"] * quantity

    spent_today = st.session_state.spent_today

    # --------------------------------------------------------
    # INVENTORY CHECK
    # --------------------------------------------------------

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
            f"Available: {inventory['available_stock']}\n\n"
            f"📋 Audit ID: `{event['audit_id']}`"
        )

    # --------------------------------------------------------
    # POLICY ENGINE
    # --------------------------------------------------------

    policy = evaluate_policy(
        product=product,
        quantity=quantity,
        budget=budget,
        spent_today=spent_today
    )

    hard_failures = []

    for key, status in policy["checks"].items():

        if status == "FAIL" and key != "transaction_limit":
            hard_failures.append(key)

    transaction_limit_review = (
        policy["checks"]["transaction_limit"] == "FAIL"
        and not hard_failures
    )

    # --------------------------------------------------------
    # RISK ENGINE
    # --------------------------------------------------------

    risk = calculate_risk(
        amount=total,
        quantity=quantity,
        stock=product["stock"],
        vendor_trusted=True,
        agent_verified=True,
        transaction_count=len(
            audit_engine.get_events()
        ),
        policy_violation=bool(hard_failures)
    )

    # --------------------------------------------------------
    # SIMULATION ENGINE
    # --------------------------------------------------------

    simulation = simulate_transaction(
        product=product,
        quantity=quantity,
        budget=budget,
        risk_result=risk,
        policy_result=policy,
        vendor_trusted=True
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if hard_failures:

        decision = "BLOCKED"

    elif risk["level"] == "HIGH":

        decision = "BLOCKED"

    elif (
        transaction_limit_review
        or risk["level"] == "MEDIUM"
        or simulation["recommendation"] == "HUMAN_REVIEW"
    ):

        decision = "HUMAN_APPROVAL_REQUIRED"

    else:

        decision = "APPROVED"

    # --------------------------------------------------------
    # EXPLAINABILITY
    # --------------------------------------------------------

    explanation = explain_decision(
        decision=decision,
        risk_result=risk,
        policy_result=policy,
        product=product,
        quantity=quantity,
        total_amount=total
    )

    # --------------------------------------------------------
    # BLOCKED
    # --------------------------------------------------------

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
                "policy_reasons": policy["reasons"],
                "hard_failures": hard_failures
            }
        )

        return (
            "🚫 **MERCHX TRANSACTION BLOCKED**\n\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"{format_risk_report(risk)}\n\n"
            f"{format_explanation(explanation)}\n\n"
            f"📋 Audit ID: `{event['audit_id']}`"
        )

    # --------------------------------------------------------
    # HUMAN APPROVAL
    # --------------------------------------------------------

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
            f"{format_explanation(explanation)}\n\n"
            "👇 Review the approval panel."
        )

    # --------------------------------------------------------
    # AUTO APPROVAL
    # --------------------------------------------------------

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
        f"📋 Audit ID: `{event['audit_id']}`"
    )


# ============================================================
# AI AGENT HANDLER
# ============================================================

def handle_message(user_input):

    intent = detect_intent(user_input)

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
    # HELP
    # --------------------------------------------------------

    if action == "HELP":

        return get_agent_response("HELP")

    # --------------------------------------------------------
    # ASK PRODUCT
    # --------------------------------------------------------

    if action == "ASK_PRODUCT":

        return (
            "🛒 **Which product are you looking for?**\n\n"
            "Examples:\n"
            "• headphones\n"
            "• laptop\n"
            "• smartwatch"
        )

    # --------------------------------------------------------
    # ORDER ID
    # --------------------------------------------------------

    if action == "ASK_ORDER_ID":

        return "📦 Please provide the order ID."

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if action == "SEARCH":

        if "keyword" in payload:

            keyword = payload["keyword"]
            budget = payload.get("budget")

            results = search_catalog(
                keyword,
                budget
            )

            memory.remember_search(
                results,
                budget,
                payload.get("quantity")
            )

            return results

        if "product" in payload:

            product = payload["product"]

            memory.remember_selection(product)

            return product

    # --------------------------------------------------------
    # SEARCH THEN BUY
    # --------------------------------------------------------

    if action == "SEARCH_THEN_BUY":

        keyword = payload["keyword"]
        budget = payload.get("budget")

        results = search_catalog(
            keyword,
            budget
        )

        memory.remember_search(
            results,
            budget,
            payload.get("quantity")
        )

        return results

    # --------------------------------------------------------
    # COMPARE
    # --------------------------------------------------------

    if action == "COMPARE":

        results = memory.last_search_results

        if not results:
            return "🔎 Search for a product first."

        if len(results) < 2:
            return "⚠️ Need at least two products to compare."

        text = "⚖️ **MERCHX SMART COMPARISON**\n\n"

        for product in results:

            text += (
                f"**{product['name']}**\n"
                f"💰 ₹{product['price']:,}\n"
                f"📦 Stock: {product['stock']}\n"
                f"⚙️ {', '.join(product['features'])}\n\n"
            )

        return text

    # --------------------------------------------------------
    # QUOTE
    # --------------------------------------------------------

    if action == "QUOTE":

        product = payload["product"]

        quantity = payload.get(
            "quantity",
            1
        )

        total = product["price"] * quantity

        quote = {
            "id": f"MX-QT-{len(audit_engine.get_events()) + 1:04d}",
            "product_id": product["id"],
            "product": product["name"],
            "quantity": quantity,
            "total": total
        }

        memory.remember_quote(quote)

        return (
            "🧾 **MERCHX PURCHASE QUOTE**\n\n"
            f"Quote ID: `{quote['id']}`\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            "Status: **VALID**\n"
            "Validity: **10 minutes**"
        )

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    if action == "INVENTORY":

        product = payload["product"]

        quantity = payload.get(
            "quantity",
            1
        )

        inventory = check_inventory(
            product["id"],
            quantity
        )

        if inventory["available"]:

            return (
                "📦 **IN STOCK**\n\n"
                f"{product['name']}\n"
                f"Available: "
                f"{inventory['available_stock']} units"
            )

        return (
            "❌ **INSUFFICIENT STOCK**\n\n"
            f"Available: "
            f"{inventory['available_stock']} units"
        )

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

        return purchase_pipeline(
            product,
            quantity,
            budget
        )

    return get_agent_response(intent)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🛡️ MERCHX CONTROL")

    st.metric(
        "Today's Spend",
        f"₹{st.session_state.spent_today:,}"
    )

    st.metric(
        "Audit Events",
        len(audit_engine.get_events())
    )

    st.divider()

    st.subheader("System Layers")

    st.write("🧠 AI Agent")
    st.write("🧩 Context Engine")
    st.write("🛒 Commerce Engine")
    st.write("⚖️ Policy Engine")
    st.write("🛡️ Risk Engine")
    st.write("🔮 Simulation Engine")
    st.write("🧠 Explainability")
    st.write("📋 Audit Engine")
    st.write("🧬 Policy Optimizer")

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
                "Audit chain integrity check failed."
            )

    if st.button(
        "🧹 Clear Chat",
        use_container_width=True
    ):

        st.session_state.chat_log = []
        st.session_state.memory = AgentMemory()
        st.session_state.pending_purchase = None

        st.rerun()


# ============================================================
# HUMAN APPROVAL PANEL
# ============================================================

pending = st.session_state.pending_purchase

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
        f"{risk['level']} — {risk['score']}/100"
    )

    with st.expander("🔎 View Details"):

        st.markdown(
            format_risk_report(risk)
        )

        st.markdown(
            format_simulation_report(
                pending["simulation"]
            )
        )

        st.markdown(
            format_explanation(
                pending["explanation"]
            )
        )

    approve_col, reject_col = st.columns(2)

    with approve_col:

        if st.button(
            "✅ APPROVE TRANSACTION",
            use_container_width=True
        ):

            event = audit_engine.record_event(
                action="HUMAN_APPROVAL",
                agent_id="AGENT-001",
                product_id=product["id"],
                amount=pending["total"],
                decision="APPROVED_BY_HUMAN",
                risk_level=risk["level"],
                policy_status="APPROVED",
                payment_status="SIMULATED_SUCCESS"
            )

            st.session_state.spent_today += pending["total"]

            st.session_state.pending_purchase = Non