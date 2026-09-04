import streamlit as st

from agent_engine import detect_intent, get_agent_response
from agent_context import AgentMemory, plan_next_step

from commerce_engine import (
    search_products,
    check_inventory,
    get_product,
)

from policy_engine import evaluate_policy

from risk_engine import calculate_risk, format_risk_report
from explainability_engine import (
    explain_decision,
    explain_alternative,
    format_explanation,
    format_counterfactual,
)
from audit_engine import AuditEngine, create_audit_summary
from simulation_engine import (
    simulate_transaction,
    format_simulation_report,
)
from policy_optimizer import (
    PolicyOptimizer,
    format_optimization_report,
)


# =========================================================
# MERCHX CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="MERCHX",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ MERCHX")
st.caption("AI-Native Commerce Protocol")


# =========================================================
# SESSION STATE
# =========================================================

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


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def product_matches_query(product, query):
    """
    Flexible product matching for short natural-language queries.
    """

    query = query.lower().strip()

    searchable = " ".join([
        product.get("name", ""),
        product.get("category", ""),
        " ".join(product.get("features", [])),
    ]).lower()

    words = [
        word.strip(".,!?")
        for word in query.split()
        if len(word.strip(".,!?")) > 2
    ]

    if not words:
        return False

    return any(word in searchable for word in words)


def search_catalog(query, budget=None):
    """
    Search the Commerce Engine while supporting
    natural-language product queries.
    """

    query = query.lower().strip()

    # First try Commerce Engine's native search.
    results = search_products(
        query,
        max_price=budget,
    )

    if results:
        return results

    # Fallback: search individual catalog words.
    all_results = []

    for word in query.split():
        if len(word) < 3:
            continue

        matches = search_products(
            word,
            max_price=budget,
        )

        for product in matches:
            if product not in all_results:
                all_results.append(product)

    return all_results


def format_products(results):
    """
    Display products in a clean MERCHX format.
    """

    if not results:
        return "❌ No matching products found."

    lines = [
        "🛒 **MERCHX PRODUCT DISCOVERY**",
        "",
    ]

    for index, product in enumerate(results, start=1):
        features = ", ".join(product.get("features", []))

        lines.append(
            f"**{index}. {product['name']}**\n"
            f"💰 ₹{product['price']:,}\n"
            f"📦 Stock: {product['stock']}\n"
            f"🏷️ Category: {product['category']}\n"
            f"⚙️ {features}\n"
            f"🆔 {product['id']}\n"
        )

    return "\n".join(lines)


def select_best_product(results, budget=None):
    """
    Select the strongest available candidate.

    Current MVP scoring:
    - Budget fit
    - Stock availability
    - Feature count
    - Price
    """

    if not results:
        return None

    candidates = results

    if budget is not None:
        within_budget = [
            product
            for product in results
            if product["price"] <= budget
        ]

        if within_budget:
            candidates = within_budget

    # Simple explainable MVP score.
    def score(product):
        stock_score = min(product["stock"], 20)
        feature_score = len(product.get("features", [])) * 5

        budget_score = 20

        if budget is not None and product["price"] > budget:
            budget_score = -50

        return (
            budget_score
            + stock_score
            + feature_score
        )

    return max(candidates, key=score)


def select_cheapest_product(results):
    if not results:
        return None

    return min(
        results,
        key=lambda product: product["price"],
    )


# =========================================================
# PURCHASE PIPELINE
# =========================================================

def run_purchase_pipeline(product, quantity=1, budget=None):
    """
    Full MERCHX authorization pipeline.

    AI requests.
    MERCHX decides.
    Payment is NOT automatically executed for blocked/review cases.
    """

    spent_today = st.session_state.spent_today

    total = product["price"] * quantity

    # -----------------------------------------------------
    # STEP 1 — INVENTORY
    # -----------------------------------------------------

    inventory = check_inventory(
        product["id"],
        quantity,
    )

    if not inventory["available"]:

        audit_engine.record_event(
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
            f"❌ **PURCHASE BLOCKED**\n\n"
            f"Product: {product['name']}\n"
            f"Requested: {quantity}\n"
            f"Available: {inventory['available_stock']}"
        )

    # -----------------------------------------------------
    # STEP 2 — POLICY
    # -----------------------------------------------------

    policy_result = evaluate_policy(
        product=product,
        quantity=quantity,
        budget=budget,
        spent_today=spent_today,
    )

    # -----------------------------------------------------
    # STEP 3 — RISK
    # -----------------------------------------------------

    risk_result = calculate_risk(
        amount=total,
        quantity=quantity,
        stock=product["stock"],
        vendor_trusted=True,
        agent_verified=True,
        transaction_count=len(audit_engine.get_events()),
        policy_violation=not policy_result["approved"],
    )

    # -----------------------------------------------------
    # STEP 4 — SIMULATION
    # -----------------------------------------------------

    simulation_result = simulate_transaction(
        product=product,
        quantity=quantity,
        budget=budget,
        risk_result=risk_result,
        policy_result=policy_result,
        vendor_trusted=True,
    )

    # -----------------------------------------------------
    # STEP 5 — DECISION
    # -----------------------------------------------------

    if not policy_result["approved"]:

        decision = "BLOCKED"

    elif risk_result["level"] == "HIGH":

        decision = "BLOCKED"

    elif (
        risk_result["level"] == "MEDIUM"
        or simulation_result["recommendation"] == "HUMAN_REVIEW"
    ):

        decision = "HUMAN_APPROVAL_REQUIRED"

    else:

        decision = "APPROVED"

    # -----------------------------------------------------
    # STEP 6 — EXPLAINABILITY
    # -----------------------------------------------------

    explanation = explain_decision(
        decision=decision,
        risk_result=risk_result,
        policy_result=policy_result,
        product=product,
        quantity=quantity,
        total_amount=total,
    )

    # -----------------------------------------------------
    # STEP 7 — BLOCK
    # -----------------------------------------------------

    if decision == "BLOCKED":

        audit_event = audit_engine.record_event(
            action="PURCHASE_BLOCKED",
            agent_id="AGENT-001",
            product_id=product["id"],
            amount=total,
            decision=decision,
            risk_level=risk_result["level"],
            policy_status=(
                "APPROVED"
                if policy_result["approved"]
                else "BLOCKED"
            ),
            payment_status="NOT_EXECUTED",
            metadata={
                "policy_reasons": policy_result["reasons"],
            },
        )

        return (
            f"🚫 **MERCHX TRANSACTION BLOCKED**\n\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"{format_risk_report(risk_result)}\n\n"
            f"{format_explanation(explanation)}\n\n"
            f"📋 Audit: {audit_event['audit_id']}"
        )

    # -----------------------------------------------------
    # STEP 8 — HUMAN APPROVAL
    # -----------------------------------------------------

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
            f"🟡 **HUMAN APPROVAL REQUIRED**\n\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"{format_risk_report(risk_result)}\n\n"
            f"{format_simulation_report(simulation_result)}\n\n"
            f"{format_explanation(explanation)}\n\n"
            f"👇 Review the approval panel below."
        )

    # -----------------------------------------------------
    # STEP 9 — APPROVED
    # -----------------------------------------------------

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
        f"✅ **MERCHX TRANSACTION APPROVED**\n\n"
        f"Product: {product['name']}\n"
        f"Quantity: {quantity}\n"
        f"Total: ₹{total:,}\n\n"
        f"{format_risk_report(risk_result)}\n\n"
        f"{format_explanation(explanation)}\n\n"
        f"💳 Payment: **SIMULATED SUCCESS**\n"
        f"📦 Order: **CREATED**\n"
        f"📋 Audit ID: **{audit_event['audit_id']}**"
    )


# =========================================================
# USER MESSAGE HANDLER
# =========================================================

def handle_user_message(user_input):
    """
    Main MERCHX conversation orchestrator.
    """

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

    # -----------------------------------------------------
    # HELP
    # -----------------------------------------------------

    if action == "HELP":
        return get_agent_response("HELP")

    # -----------------------------------------------------
    # ASK PRODUCT
    # -----------------------------------------------------

    if action == "ASK_PRODUCT":

        return (
            "🛒 Sure. Which product are you looking for?\n\n"
            "Examples:\n"
            "• headphones\n"
            "• laptop\n"
            "• smartwatch"
        )

    # -----------------------------------------------------
    # ASK ORDER ID
    # -----------------------------------------------------

    if action == "ASK_ORDER_ID":

        return "📦 Please provide the order ID."

    # -----------------------------------------------------
    # SEARCH
    # -----------------------------------------------------

    if action == "SEARCH":

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

    # -----------------------------------------------------
    # SEARCH THEN BUY
    # -----------------------------------------------------

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
            "👉 Say **best**, **cheapest**, or the exact product name."
        )

    # -----------------------------------------------------
    # COMPARE
    # -----------------------------------------------------

    if action == "COMPARE":

        results = memory.last_search_results

        if not results:
            return "🔎 Search for a product first."

        if len(results) < 2:
            return "Need at least two products to compare."

        lines = [
            "⚖️ **MERCHX SMART COMPARISON**",
            "",
        ]

        for product in results:
            lines.append(
                f"**{product['name']}**\n"
                f"💰 ₹{product['price']:,}\n"
                f"📦 Stock: {product['stock']}\n"
                f"⚙️ {', '.join(product['features'])}\n"
            )

        return "\n".join(lines)

    # -----------------------------------------------------
    # QUOTE
    # -----------------------------------------------------

    if action == "QUOTE":

        product = payload["product"]
        quantity = payload.get("quantity", 1)

        total = product["price"] * quantity

        quote = {
            "id": f"MX-QT-{len(audit_engine.get_events()) + 1:04d}",
            "product_id": product["id"],
            "product": product["name"],
            "quantity": quantity,
            "total": total,
        }

        memory.remember_quote(quote)

        return (
            f"🧾 **MERCHX VERIFIED QUOTE**\n\n"
            f"Quote ID: {quote['id']}\n"
            f"Product: {product['name']}\n"
            f"Quantity: {quantity}\n"
            f"Total: ₹{total:,}\n\n"
            f"Status: VALID\n"
            f"Validity: 10 minutes"
        )

    # -----------------------------------------------------
    # INVENTORY
    # -----------------------------------------------------

    if action == "INVENTORY":

        product = payload["product"]

        inventory = check_inventory(
            product["id"],
            payload.get("quantity", 1),
        )

        if inventory["available"]:

            return (
                f"📦 **IN STOCK**\n\n"
                f"{product['name']}\n"
                f"Available: {inventory['available_stock']} units"
            )

        return (
            f"❌ **INSUFFICIENT STOCK**\n\n"
            f"Available: {inventory['available_stock']} units"
        )

    # -----------------------------------------------------
    # PURCHASE
    # -----------------------------------------------------

    if action == "RUN_PURCHASE_PIPELINE":

        product = payload["product"]
        quantity = payload.get("quantity", 1)

        budget = memory.budget_hint

        return run_purchase_pipeline(
            product,
            quantity,
            budget,
        )

    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    return get_agent_response(intent)


# =========================================================
# SIDEBAR — SYSTEM STATUS
# =========================================================

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

    if st.button("🔍 Verify Audit Integrity"):

        valid = audit_engine.verify_integrity()

        if valid:
            st.success("Audit chain integrity verified.")
        else:
            st.error("Audit chain integrity check failed.")

    if st.button("🧹 Clear Chat"):

        st.session_state.chat_log = []
        st.rerun()


# =========================================================
# HUMAN APPROVAL PANEL
# =========================================================

pending = st.session_state.pending_purchase

if pending:

    st.warning("🟡 HUMAN-IN-THE-LOOP APPROVAL")

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
        f"**Risk:** {risk['level']} — {risk['score']}/100"
    )

    col1, col2 = st.columns(2)

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

            st.session_state.spent_today += pending["total"]

            st.session_state.pending_purchase = None

            st.success(
                "Transaction approved by human authority."
            )

            st.info(
                f"💳 Simulated payment successful\n\n"
                f"📦 Order created\n\n"
                f"📋 Audit ID: {audit_event['audit_id']}"
            )

            st.rerun()

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
                risk_level=risk["level"],
                policy_status="REVIEW",
                payment_status="NOT_EXECUTED",
            )

            st.session_state.pending_purchase = None

            st.error(
                f"Transaction rejected.\n\n"
                f"Audit ID: {audit_event['audit_id']}"
            )

            st.rerun()


# =========================================================
# CHAT HISTORY
# =========================================================

for entry in st.session_state.chat_log:

    with st.chat_message(entry["role"]):

        st.markdown(entry["text"])


# =======================================