# MERCHX Risk Engine
# Evaluates transaction risk using explainable rules.
# Output: LOW / MEDIUM / HIGH + score + reasons


def calculate_risk(
    amount,
    quantity=1,
    stock=0,
    vendor_trusted=True,
    agent_verified=True,
    transaction_count=0,
    policy_violation=False,
):
    """
    Calculate an explainable risk score for a commerce transaction.

    Returns:
        {
            "score": int,
            "level": "LOW" | "MEDIUM" | "HIGH",
            "reasons": list[str],
            "decision": str
        }
    """

    score = 0
    reasons = []

    # -------------------------------------------------
    # 1. Transaction amount
    # -------------------------------------------------
    if amount >= 25000:
        score += 30
        reasons.append("High transaction value")

    elif amount >= 10000:
        score += 20
        reasons.append("Above normal transaction value")

    elif amount >= 5000:
        score += 10
        reasons.append("Moderate transaction value")

    # -------------------------------------------------
    # 2. Quantity
    # -------------------------------------------------
    if quantity >= 10:
        score += 20
        reasons.append("Large purchase quantity")

    elif quantity >= 5:
        score += 10
        reasons.append("Higher-than-normal purchase quantity")

    # -------------------------------------------------
    # 3. Stock pressure
    # -------------------------------------------------
    if stock > 0 and quantity >= stock:
        score += 20
        reasons.append("Purchase consumes available stock")

    elif stock > 0 and quantity >= max(1, int(stock * 0.5)):
        score += 10
        reasons.append("Purchase consumes a significant portion of stock")

    # -------------------------------------------------
    # 4. Vendor trust
    # -------------------------------------------------
    if not vendor_trusted:
        score += 20
        reasons.append("Vendor trust is low or unknown")

    # -------------------------------------------------
    # 5. Agent identity
    # -------------------------------------------------
    if not agent_verified:
        score += 25
        reasons.append("Agent identity is not verified")

    # -------------------------------------------------
    # 6. Transaction frequency
    # -------------------------------------------------
    if transaction_count >= 20:
        score += 20
        reasons.append("Unusually high transaction frequency")

    elif transaction_count >= 10:
        score += 10
        reasons.append("Elevated transaction frequency")

    # -------------------------------------------------
    # 7. Policy violation
    # -------------------------------------------------
    if policy_violation:
        score += 40
        reasons.append("Policy violation detected")

    # -------------------------------------------------
    # Keep score between 0 and 100
    # -------------------------------------------------
    score = min(score, 100)

    # -------------------------------------------------
    # Risk level
    # -------------------------------------------------
    if score <= 30:
        level = "LOW"
        decision = "AUTO_APPROVAL_ELIGIBLE"

    elif score <= 70:
        level = "MEDIUM"
        decision = "HUMAN_APPROVAL_REQUIRED"

    else:
        level = "HIGH"
        decision = "BLOCK_TRANSACTION"

    # If no negative signals exist
    if not reasons:
        reasons.append("No significant risk indicators detected")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "decision": decision,
    }


def format_risk_report(risk_result):
    """
    Convert risk result into a human-readable MERCHX report.
    """

    score = risk_result["score"]
    level = risk_result["level"]
    decision = risk_result["decision"]
    reasons = risk_result["reasons"]

    report = [
        "🛡️ MERCHX RISK ASSESSMENT",
        "",
        f"Risk Score: {score}/100",
        f"Risk Level: {level}",
        f"Decision: {decision}",
        "",
        "Why:",
    ]

    for reason in reasons:
        report.append(f"• {reason}")

    return "\n".join(report)


def is_transaction_safe(risk_result):
    """
    Returns True only for LOW-risk transactions.
    """

    return risk_result["level"] == "LOW"


def requires_human_approval(risk_result):
    """
    Returns True when MERCHX requires human approval.
    """

    return risk_result["level"] == "MEDIUM"


def should_block(risk_result):
    """
    Returns True when the transaction should be blocked.
    """

    return risk_result["level"] == "HIGH"