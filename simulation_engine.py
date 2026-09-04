# MERCHX Simulation Engine
# Simulates possible transaction outcomes before execution.
# This is a decision-support layer, not a payment executor.


def simulate_transaction(
    product,
    quantity=1,
    budget=None,
    risk_result=None,
    policy_result=None,
    vendor_trusted=True,
):
    """
    Simulate a purchase before execution.

    Returns multiple possible scenarios and a recommended action.
    """

    price = product.get("price", 0)
    stock = product.get("stock", 0)
    name = product.get("name", "Unknown Product")

    total = price * quantity

    scenarios = []

    # -------------------------------------------------
    # Scenario 1: Normal execution
    # -------------------------------------------------

    if stock >= quantity:
        scenarios.append({
            "name": "Normal Execution",
            "status": "SUCCESS",
            "message": "Product is available and quantity can be fulfilled.",
        })
    else:
        scenarios.append({
            "name": "Normal Execution",
            "status": "FAIL",
            "message": f"Insufficient stock. Only {stock} units available.",
        })

    # -------------------------------------------------
    # Scenario 2: Budget impact
    # -------------------------------------------------

    if budget is not None:

        if total <= budget:
            scenarios.append({
                "name": "Budget Check",
                "status": "SUCCESS",
                "message": (
                    f"Purchase is within budget. "
                    f"₹{budget - total:,} budget remains."
                ),
            })
        else:
            scenarios.append({
                "name": "Budget Check",
                "status": "FAIL",
                "message": (
                    f"Purchase exceeds budget by "
                    f"₹{total - budget:,}."
                ),
            })

    else:
        scenarios.append({
            "name": "Budget Check",
            "status": "INFO",
            "message": "No explicit budget was provided.",
        })

    # -------------------------------------------------
    # Scenario 3: Stock pressure
    # -------------------------------------------------

    if stock > 0:

        remaining_stock = stock - quantity

        if remaining_stock < 0:
            scenarios.append({
                "name": "Stock Pressure",
                "status": "FAIL",
                "message": "Requested quantity exceeds available stock.",
            })

        elif remaining_stock == 0:
            scenarios.append({
                "name": "Stock Pressure",
                "status": "WARNING",
                "message": "Purchase would consume all remaining stock.",
            })

        elif remaining_stock <= max(1, int(stock * 0.2)):
            scenarios.append({
                "name": "Stock Pressure",
                "status": "WARNING",
                "message": (
                    f"Only {remaining_stock} units would remain "
                    "after this purchase."
                ),
            })

        else:
            scenarios.append({
                "name": "Stock Pressure",
                "status": "SUCCESS",
                "message": f"{remaining_stock} units would remain.",
            })

    # -------------------------------------------------
    # Scenario 4: Vendor trust
    # -------------------------------------------------

    if vendor_trusted:
        scenarios.append({
            "name": "Vendor Trust",
            "status": "SUCCESS",
            "message": "Vendor is currently trusted.",
        })
    else:
        scenarios.append({
            "name": "Vendor Trust",
            "status": "WARNING",
            "message": "Vendor trust is low or unknown.",
        })

    # -------------------------------------------------
    # Scenario 5: Risk outcome
    # -------------------------------------------------

    if risk_result:

        risk_level = risk_result.get("level", "UNKNOWN")
        risk_score = risk_result.get("score", 0)

        if risk_level == "LOW":
            scenarios.append({
                "name": "Risk Outcome",
                "status": "SUCCESS",
                "message": f"LOW risk detected ({risk_score}/100).",
            })

        elif risk_level == "MEDIUM":
            scenarios.append({
                "name": "Risk Outcome",
                "status": "WARNING",
                "message": (
                    f"MEDIUM risk detected ({risk_score}/100). "
                    "Human approval may be required."
                ),
            })

        elif risk_level == "HIGH":
            scenarios.append({
                "name": "Risk Outcome",
                "status": "FAIL",
                "message": (
                    f"HIGH risk detected ({risk_score}/100). "
                    "Transaction should be blocked."
                ),
            })

    # -------------------------------------------------
    # Scenario 6: Policy outcome
    # -------------------------------------------------

    if policy_result:

        policy_status = policy_result.get(
            "status",
            policy_result.get("decision", "UNKNOWN"),
        )

        scenarios.append({
            "name": "Policy Outcome",
            "status": "INFO",
            "message": f"Policy result: {policy_status}.",
        })

    # -------------------------------------------------
    # Final recommendation
    # -------------------------------------------------

    has_failure = any(
        scenario["status"] == "FAIL"
        for scenario in scenarios
    )

    has_warning = any(
        scenario["status"] == "WARNING"
        for scenario in scenarios
    )

    if has_failure:
        recommendation = "BLOCK_OR_REVIEW"

    elif has_warning:
        recommendation = "HUMAN_REVIEW"

    else:
        recommendation = "SAFE_TO_CONTINUE"

    return {
        "product": name,
        "quantity": quantity,
        "total": total,
        "scenarios": scenarios,
        "recommendation": recommendation,
    }


def run_what_if(
    product,
    quantities,
    budget=None,
):
    """
    Compare multiple quantities before purchase.
    """

    results = []

    price = product.get("price", 0)
    stock = product.get("stock", 0)

    for quantity in quantities:

        total = price * quantity
        within_stock = quantity <= stock

        if budget is not None:
            within_budget = total <= budget
        else:
            within_budget = True

        if within_stock and within_budget:
            status = "FEASIBLE"
        elif not within_stock:
            status = "OUT_OF_STOCK"
        else:
            status = "OVER_BUDGET"

        results.append({
            "quantity": quantity,
            "total": total,
            "status": status,
        })

    return results


def format_simulation_report(simulation):
    """
    Convert simulation results into a readable MERCHX report.
    """

    lines = [
        "🔮 MERCHX PRE-PURCHASE SIMULATION",
        "",
        f"Product: {simulation['product']}",
        f"Quantity: {simulation['quantity']}",
        f"Total: ₹{simulation['total']:,}",
        "",
        "POSSIBLE OUTCOMES:",
    ]

    for scenario in simulation["scenarios"]:
        status = scenario["status"]

        if status == "SUCCESS":
            icon = "✅"
        elif status == "WARNING":
            icon = "⚠️"
        elif status == "FAIL":
            icon = "❌"
        else:
            icon = "ℹ️"

        lines.append(
            f"{icon} {scenario['name']}: {scenario['message']}"
        )

    lines.extend([
        "",
        f"RECOMMENDATION: {simulation['recommendation']}",
    ])

    return "\n".join(lines)


def format_what_if(results):
    """
    Format what-if quantity analysis.
    """

    lines = [
        "🔮 MERCHX WHAT-IF ANALYSIS",
        "",
    ]

    for result in results:
        lines.append(
            f"Quantity {result['quantity']} → "
            f"₹{result['total']:,} → {result['status']}"
        )

    return "\n".join(lines)