# MERCHX Explainability Engine
# Explains WHY MERCHX approved, reviewed, or blocked a transaction.
# Also explains WHY an alternative product was not selected.


def explain_decision(
    decision,
    risk_result=None,
    policy_result=None,
    product=None,
    quantity=1,
    total_amount=0,
):
    """
    Generate a human-readable explanation for a MERCHX decision.
    """

    explanation = {
        "decision": decision,
        "summary": "",
        "reasons": [],
        "recommendation": "",
    }

    decision_upper = str(decision).upper()

    # -------------------------------------------------
    # Decision summary
    # -------------------------------------------------

    if "APPROV" in decision_upper:
        explanation["summary"] = (
            "MERCHX approved this transaction because it passed "
            "the required commerce, policy, and risk checks."
        )

    elif "BLOCK" in decision_upper:
        explanation["summary"] = (
            "MERCHX blocked this transaction because one or more "
            "security, policy, or risk conditions were not satisfied."
        )

    elif "HUMAN" in decision_upper or "REVIEW" in decision_upper:
        explanation["summary"] = (
            "MERCHX requires human approval because the transaction "
            "has conditions that should be reviewed before payment."
        )

    else:
        explanation["summary"] = (
            "MERCHX evaluated the transaction and generated a decision."
        )

    # -------------------------------------------------
    # Product information
    # -------------------------------------------------

    if product:
        explanation["reasons"].append(
            f"Product evaluated: {product.get('name', 'Unknown product')}"
        )

    if quantity:
        explanation["reasons"].append(
            f"Quantity requested: {quantity}"
        )

    if total_amount:
        explanation["reasons"].append(
            f"Transaction value: ₹{total_amount:,}"
        )

    # -------------------------------------------------
    # Risk explanation
    # -------------------------------------------------

    if risk_result:
        risk_score = risk_result.get("score")
        risk_level = risk_result.get("level")

        if risk_score is not None:
            explanation["reasons"].append(
                f"Risk assessment: {risk_level} ({risk_score}/100)"
            )

        for reason in risk_result.get("reasons", []):
            explanation["reasons"].append(
                f"Risk factor: {reason}"
            )

    # -------------------------------------------------
    # Policy explanation
    # -------------------------------------------------

    if policy_result:
        policy_status = policy_result.get(
            "status",
            policy_result.get("decision", "UNKNOWN")
        )

        explanation["reasons"].append(
            f"Policy evaluation: {policy_status}"
        )

        policy_reasons = policy_result.get("reasons", [])

        for reason in policy_reasons:
            explanation["reasons"].append(
                f"Policy factor: {reason}"
            )

    # -------------------------------------------------
    # Recommendation
    # -------------------------------------------------

    if "APPROV" in decision_upper:
        explanation["recommendation"] = (
            "Proceed to the next authorized commerce step."
        )

    elif "HUMAN" in decision_upper or "REVIEW" in decision_upper:
        explanation["recommendation"] = (
            "Request human approval before allowing payment."
        )

    elif "BLOCK" in decision_upper:
        explanation["recommendation"] = (
            "Do not execute payment. Resolve the blocking condition first."
        )

    else:
        explanation["recommendation"] = (
            "Review the transaction before continuing."
        )

    return explanation


def explain_alternative(
    selected_product,
    alternative_product,
    budget=None,
    preferred_vendor=None,
):
    """
    Explain why one product was selected instead of another.
    This is MERCHX counterfactual explainability.
    """

    reasons = []

    selected_price = selected_product.get("price", 0)
    alternative_price = alternative_product.get("price", 0)

    # -------------------------------------------------
    # Budget comparison
    # -------------------------------------------------

    if budget is not None:

        if alternative_price > budget:
            reasons.append(
                f"Alternative exceeds the budget by "
                f"₹{alternative_price - budget:,}."
            )

        elif selected_price <= budget and alternative_price <= budget:
            reasons.append(
                "Both products are within the requested budget."
            )

    # -------------------------------------------------
    # Price comparison
    # -------------------------------------------------

    if selected_price < alternative_price:
        reasons.append(
            f"Selected product is ₹{alternative_price - selected_price:,} cheaper."
        )

    elif selected_price > alternative_price:
        reasons.append(
            f"Alternative is ₹{selected_price - alternative_price:,} cheaper."
        )

    else:
        reasons.append("Both products have the same price.")

    # -------------------------------------------------
    # Stock comparison
    # -------------------------------------------------

    selected_stock = selected_product.get("stock", 0)
    alternative_stock = alternative_product.get("stock", 0)

    if selected_stock > alternative_stock:
        reasons.append(
            "Selected product has better stock availability."
        )

    elif alternative_stock > selected_stock:
        reasons.append(
            "Alternative product has better stock availability."
        )

    # -------------------------------------------------
    # Vendor preference
    # -------------------------------------------------

    if preferred_vendor:
        if selected_product.get("vendor") == preferred_vendor:
            reasons.append(
                f"Selected vendor matches the preferred vendor: {preferred_vendor}."
            )

        elif alternative_product.get("vendor") != preferred_vendor:
            reasons.append(
                "Neither option matches the preferred vendor."
            )

    return {
        "selected": selected_product.get("name", "Unknown"),
        "alternative": alternative_product.get("name", "Unknown"),
        "reasons": reasons,
    }


def format_explanation(explanation):
    """
    Convert explanation data into a clean MERCHX UI message.
    """

    lines = [
        "🧠 MERCHX DECISION EXPLANATION",
        "",
        f"Decision: {explanation.get('decision', 'UNKNOWN')}",
        "",
        explanation.get("summary", ""),
        "",
        "WHY?",
    ]

    for reason in explanation.get("reasons", []):
        lines.append(f"• {reason}")

    lines.extend(
        [
            "",
            "RECOMMENDATION:",
            f"→ {explanation.get('recommendation', '')}",
        ]
    )

    return "\n".join(lines)


def format_counterfactual(result):
    """
    Format a 'Why this product instead of that one?' explanation.
    """

    lines = [
        "🔍 MERCHX COUNTERFACTUAL ANALYSIS",
        "",
        f"Selected: {result.get('selected', 'Unknown')}",
        f"Alternative: {result.get('alternative', 'Unknown')}",
        "",
        "WHY SELECTED?",
    ]

    for reason in result.get("reasons", []):
        lines.append(f"• {reason}")

    return "\n".join(lines)