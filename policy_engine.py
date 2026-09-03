# MERCHX Policy Engine
# Independent authorization layer

MAX_TRANSACTION = 10000
DAILY_LIMIT = 20000
MAX_QUANTITY = 3

ALLOWED_CATEGORIES = [
    "Electronics",
    "Accessories",
]


def evaluate_policy(
    product,
    quantity,
    budget=None,
    spent_today=0,
):
    """
    Evaluate a commerce request against
    MERCHX security policies.

    Returns:
        approved: True / False
        reasons: list of policy violations
        checks: detailed policy results
    """

    reasons = []

    checks = {
        "transaction_limit": "PASS",
        "daily_limit": "PASS",
        "quantity_limit": "PASS",
        "budget": "PASS",
        "category": "PASS",
    }

    total = product["price"] * quantity

    # ------------------------------------------
    # TRANSACTION LIMIT
    # ------------------------------------------

    if total > MAX_TRANSACTION:

        checks["transaction_limit"] = "FAIL"

        reasons.append(
            "Transaction limit exceeded."
        )

    # ------------------------------------------
    # DAILY SPENDING LIMIT
    # ------------------------------------------

    if spent_today + total > DAILY_LIMIT:

        checks["daily_limit"] = "FAIL"

        reasons.append(
            "Daily spending limit exceeded."
        )

    # ------------------------------------------
    # QUANTITY LIMIT
    # ------------------------------------------

    if quantity > MAX_QUANTITY:

        checks["quantity_limit"] = "FAIL"

        reasons.append(
            f"Maximum quantity is {MAX_QUANTITY}."
        )

    # ------------------------------------------
    # BUDGET
    # ------------------------------------------

    if budget is not None and total > budget:

        checks["budget"] = "FAIL"

        reasons.append(
            "Requested budget exceeded."
        )

    # ------------------------------------------
    # CATEGORY
    # ------------------------------------------

    if product["category"] not in ALLOWED_CATEGORIES:

        checks["category"] = "FAIL"

        reasons.append(
            "Product category is not allowed."
        )

    approved = len(reasons) == 0

    return {
        "approved": approved,
        "total": total,
        "checks": checks,
        "reasons": reasons,
    }