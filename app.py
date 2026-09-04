import streamlit as st

from agent_engine import detect_intent, get_agent_response
from agent_context import AgentMemory, plan_next_step

from commerce_engine import (
    search_products,
    check_inventory,
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

from policy_optimizer import PolicyOptimizer, format_optimization_report


# ============================================================
# MERCHX CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="MERCHX",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ MERCHX")
st.caption("AI-Native Commerce Protocol")


# ============================================================
# SESSION STATE
# ============================================================

memory = st.session_state.setdefault(
    "memory",
    AgentMemory(),
)

audit_engine = st.session_state.setdefault(
    "audit_engine",
    AuditEngine(),
)

policy_optimizer = st.session_state.setdefault(
    "policy_optimizer",
    PolicyOptimizer(),
)

st.session_state.setdefault("chat_log", [])
st.session_state.setdefault("spent_today", 0)
st.session_state.setdefault("pending_purchase", None)


# ============================================================
# PRODUCT SEARCH
# ============================================================

def search_catalog(query, budget=None):
    """
    Search MERCHX catalog.
    """

    query = query.lower().strip()

    results = search_products(
        query,
        max_price=budget,
    )

    if results:
        return results

    # Fallback word-based search
    combined_results = []

    for word in query.split():

        if len(word) < 3:
            continue

        matches = search_products(
            word,
            max_price=budget,
        )

        for product in matches:
            if product not in combined_results:
                combined_results.append(product)

    return combined_results


# ============================================================
# PRODUCT DISPLAY
# ============================================================

def format_products(results):

    if not results:
        return "❌ **No matching products found.**"

    lines = [
        "🛒 **MERCHX PRODUCT DISCOVERY**",
        "",
    ]

    for index, product in enumerate(results, start=1):

        features = ", ".join(
            product.get("features", [])
        )

        lines.append(
            f"### {index}. {product['name']}\n"
            f"💰 **₹{product['price']:,}**\n"
            f"📦 Stock: **{product['stock']}**\n"
            f"🏷️ Category: **{product['category']}**\n"
            f"⚙️ Features: {features}\n"
            f"🆔 Product ID: `{product['id']}`\n"
        )

    return "\n".join(lines)


# ============================================================
# PURCHASE PIPELINE
# ============================================================

def run_purchase_pipeline(
    product,
    quantity=1,
    budget=None,
):

    spent_today = st.session_state.spent_today

    total = product["price"] * quantity


    # --------------------------------------------------------
    # 1. INVENTORY CHECK
    # --------------------------------------------------------

    inventory = check_inventory(
        product["id"],
        quantity,
    )

    if not inventory["available"]:

        audit_event = audit_engine.record_event(
            action="PURCHASE_BLOCKED",
            agent_id="AGENT-001",
            product_id=product["id"],
            amount=total,
            decision="BLOCKED",
            risk_level="HIGH",
            policy_status="INVENTORY_FAIL",
            payment_status="NOT_EXECUTED",
        )

        return (
            "🚫 **PURCHASE BLOCKED**\n\n"
            f"Product: {product['name']}\n"
            f"Requested Quantity: {quantity}\n"
            f"Available Stock: {inventory['available_stock']}\n\n"
            f"📋 Audit ID: `{audit_event['audit_id']}`"
        )


    # --------------------------------------------------------
    # 2. POLICY ENGINE
    # --------------------------------------------------------

    policy_result = evaluate_policy(
        product=product,
        quantity=quantity,
        budget=budget,
        spent_today=spent_today,
    )


    # --------------------------------------------------------
    # 3. HARD POLICY FAILURES
    #
    # Transaction limit can go to HITL.
    # Other policy violations remain hard blocks.
    # --------------------------------------------------------

    hard_failures = []

    for key, status in policy_result["checks"].items():

        if status == "FAIL" and key != "transaction_limit":
            hard_failures.append(key)


    transaction_limit_review = (
        policy_result["checks"]["transaction_limit"] == "FAIL"
        and not hard_failures
    )


    # --------------------------------------------------------
    # 4. RISK ENGINE
    # --------------------------------------------------------

    risk_result = calculate_risk(
        amount=total,
        quantity=quantity,
        stock=product["stock"],
        vendor_trusted=True,
        agent_verified=True,
        transaction_count=len(
            audit_engine.get_events()
        ),
        policy_violation=bool(hard_failures),
    )


    # --------------------------------------------------------
    # 5. SIMULATION ENGINE
    # --------------------------------------------------------

    simulation_result = simulate_transaction(
        product=product,
        quantity=quantity,
        budget=budget,
        risk_result=risk_result,
        policy_result=policy_result,
        vendor_trusted=True,
    )


    # --------------------------------------------------------
    # 6. FINAL DECISION
    # --------------------------------------------------------

    if hard_failures:

        decision = "BLOCKED"

    elif risk_result["level"] == "HIGH":

        decision = "BLOCKED"

    elif (
        transaction_limit_review
        or risk_result["level"] == "MEDIUM"
        or simulation_result["recommendation"] == "HUMAN_REVIEW"
    ):

        decision = "HUMAN_APPROVAL_REQUIRED"

    else:

        decision = "APPROVED"


    # --------------------------------------------------------
    # 7. EXPLAINABLE DECISION
    # --------------------------------------------------------

    explanation = explain_decision(
        decision=decision,
        risk_result=risk_result,
        policy_result=policy_result,
        product=product,
        quantity=quantity,
        total_amount=total,
    )


    # ========================================================
    # BLOCKED
    # ========================================================

    if decision == "BLOCKED":

        audit_event = audit_engine.record_event(
            action="PURCHASE_BLOCKED",
            agent_id="AGENT-001",
            product_id=product["id"],
            amount=total,
            decision="BLOCKED",
            risk_level=risk_result["level"],
            policy_status=(
                "BLOCKED"
                if hard_failures
                else "RISK_BLOCKED"
            ),
            payment_status="NOT_EXECUTED",
            metadata={
                "policy_reasons": policy_result["reasons"],
                "hard_failures": hard_failures,
            },
        )

        return (
            "🚫 **MERCHX TRANSACTION BLOCKED**\n\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"{format_risk_report(risk_result)}\n\n"
            f"{format_explanation(explanation)}\n\n"
            f"📋 Audit ID: `{audit_event['audit_id']}`"
        )


    # ========================================================
    # HUMAN APPROVAL
    # ========================================================

    if decision == "HUMAN_APPROVAL_REQUIRED":

        st.session_state.pending_purchase = {
            "product": product,
            "quantity": quantity,
            "budget": budget,
            "total": total,
            "policy": policy_result,
            "risk": risk_result,
            "simulation": simulation_result,
            "explanation": explanation,
        }

        return (
            "🟡 **HUMAN APPROVAL REQUIRED**\n\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"{format_risk_report(risk_result)}\n\n"
            f"{format_simulation_report(simulation_result)}\n\n"
            f"{format_explanation(explanation)}\n\n"
            "👇 Review the approval panel below."
        )


    # ========================================================
    # AUTO APPROVED
    # ========================================================

    audit_event = audit_engine.record_event(
        action="PURCHASE_APPROVED",
        agent_id="AGENT-001",
        product_id=product["id"],
        amount=total,
        decision="APPROVED",
        risk_level=risk_result["level"],
        policy_status="APPROVED",
        payment_status="SIMULATED_SUCCESS",
    )

    st.session_state.spent_today += total

    return (
        "✅ **MERCHX TRANSACTION APPROVED**\n\n"
        f"Product: {product['name']}\n"
        f"Quantity: {quantity}\n"
        f"Total: ₹{total:,}\n\n"
        f"{format_risk_report(risk_result)}\n\n"
        f"{format_explanation(explanation)}\n\n"
        "💳 Payment: **SIMULATED SUCCESS**\n"
        "📦 Order: **CREATED**\n"
        f"📋 Audit ID: `{audit_event['audit_id']}`"
    )


# ============================================================
# AI AGENT HANDLER
# ============================================================

def handle_user_message(user_input):

    intent = detect_intent(user_input)

    step = plan_next_step(
        intent,
        user_input,
        memory,
    )

    memory.log(
        user_input,
        intent,
        step,
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
            "🛒 **Sure! Which product are you looking for?**\n\n"
            "Examples:\n"
            "• headphones\n"
            "• laptop\n"
            "• smartwatch"
        )


    # --------------------------------------------------------
    # ASK ORDER ID
    # --------------------------------------------------------

    if action == "ASK_ORDER_ID":

        return "📦 Please provide the order ID."


    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if action == "SEARCH":

        # FIX: Handles normal keyword search
        if "keyword" in payload:

            keyword = payload["keyword"]

            budget = payload.get("budget")

            results = search_catalog(
                keyword,
                budget,
            )

            memory.remember_search(
                results,
                budget,
                payload.get("quantity"),
            )

            return format_products(results)


        # FIX: Handles "best" / "cheapest"
        elif "product" in payload:

            product = payload["product"]

            memory.remember_selection(product)

            return (
                "🎯 **MERCHX SELECTED PRODUCT**\n\n"
                f"**{product['name']}**\n\n"
                f"💰 Price: ₹{product['price']:,}\n"
                f"📦 Stock: {product['stock']}\n"
                f"🏷️ Category: {product['category']}\n"
                f"⚙️ {', '.join(product['features'])}\n\n"
                "👉 Say **buy** to continue."
            )


    # --------------------------------------------------------
    # SEARCH THEN BUY
    # --------------------------------------------------------

    if action == "SEARCH_THEN_BUY":

        keyword = payload["keyword"]

        budget = payload.get("budget")

        results = search_catalog(
            keyword,
            budget,
        )

        memory.remember_search(
            results,
            budget,
            payload.get("quantity"),
        )

        return (
            format_products(results)
            + "\n\n"
            "👉 Say **best**, **cheapest**, "
            "or the exact product name."
        )


    # --------------------------------------------------------
    # COMPARE
    # --------------------------------------------------------

    if action == "COMPARE":

        results = memory.last_search_results

        if not results:

            return "🔎 Search for a product first."


        if len(results) < 2:

            return (
                "⚠️ Need at least two products "
                "to compare."
            )


        lines = [
            "⚖️ **MERCHX SMART COMPARISON**",
            "",
        ]

        for product in results:

            lines.append(
                f"### {product['name']}\n"
                f"💰 ₹{product['price']:,}\n"
                f"📦 Stock: {product['stock']}\n"
                f"⚙️ {', '.join(product['features'])}\n"
            )

        return "\n".join(lines)


    # --------------------------------------------------------
    # QUOTE
    # --------------------------------------------------------

    if action == "QUOTE":

        product = payload["product"]

        quantity = payload.get(
            "quantity",
            1,
        )

        total = product["price"] * quantity

        quote = {
            "id": (
                f"MX-QT-"
                f"{len(audit_engine.get_events()) + 1:04d}"
            ),
            "product_id": product["id"],
            "product": product["name"],
            "quantity": quantity,
            "total": total,
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
            1,
        )

        inventory = check_inventory(
            product["id"],
            quantity,
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
    # PURCHASE
    # --------------------------------------------------------

    if action == "RUN_PURCHASE_PIPELINE":

        product = payload["product"]

        quantity = payload.get(
            "quantity",
            1,
        )

        budget = memory.budget_hint

        return run_purchase_pipeline(
            product,
            quantity,
            budget,
        )


    return get_agent_response(intent)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🛡️ MERCHX Control")

    st.metric(
        "Today's Spend",
        f"₹{st.session_state.spent_today:,}",
    )

    st.metric(
        "Audit Events",
        len(audit_engine.get_events()),
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
        use_container_width=True,
    ):

        valid = audit_engine.verify_integrity()

        if valid:

            st.success(
                "Audit chain integrity verified."
            )

        else:

            st.error(
                "Audit chain integrity check failed."
            )


    if st.button(
        "🧹 Clear Chat",
        use_container_width=True,
    ):

        st.session_state.chat_log = []

        st.rerun()


# ============================================================
# HUMAN-IN-THE-LOOP PANEL
# ============================================================

pending = st.session_state.pending_purchase


if pending:

    st.warning(
        "🟡 HUMAN-IN-THE-LOOP APPROVAL"
    )

    product = pending["product"]

    risk = pending["risk"]

    simulation = pending["simulation"]


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


    with st.expander(
        "🔎 View Risk & Simulation Details"
    ):

        st.markdown(
            format_risk_report(risk)
        )

        st.markdown(
            format_simulation_report(
                simulation
            )
        )


    col1, col2 = st.columns(2)


    # --------------------------------------------------------
    # HUMAN APPROVE
    # --------------------------------------------------------

    with col1:

        if st.button(
            "✅ APPROVE TRANSACTION",
            use_container_width=True,
        ):

            audit_event = audit_engine.record_event(
                action="HUMAN_APPROVAL",
                agent_id="AGENT-001",
                product_id=product["id"],
                amount=pending["total"],
                decision="APPROVED_BY_HUMAN",
                risk_level=risk["level"],
                policy_status="APPROVED",
                payment_status="SIMULATED_SUCCESS",
            )

            st.session_state.spent_today += (
                pending["total"]
            )

            st.session_state.pending_purchase = None

            st.success(
                "Transaction approved by human authority."
            )

            st.info(
                "💳 Simulated payment successful\n\n"
                "📦 Order created\n\n"
                f"📋 Audit ID: "
                f"`{audit_event['audit_id']}`"
            )

            st.rerun()


    # --------------------------------------------------------
    # HUMAN REJECT
    # --------------------------------------------------------

    with col2:

        if st.button(
            "❌ REJECT TRANSACTION",
            use_container_width=True,
        ):

            audit_event = audit_engine.record_event(
                action="HUMAN_REJECTION",
                agent_id="AGENT-001",
                product_id=product["id"],
                amount=pending["total"],
                decision="REJECTED_BY_HUMAN",
                risk_level