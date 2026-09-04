# MERCHX Policy Optimizer
# Analyzes historical transaction outcomes and generates
# human-reviewable policy improvement proposals.
#
# IMPORTANT:
# This engine NEVER changes policy automatically.
# It only recommends changes. A human must approve them.


DEFAULT_POLICY = {
    "auto_approval_limit": 10000,
    "daily_spend_limit": 20000,
    "max_quantity_per_order": 5,
}


class PolicyOptimizer:
    def __init__(self, current_policy=None):
        self.current_policy = (
            current_policy.copy()
            if current_policy
            else DEFAULT_POLICY.copy()
        )

    def analyze_transactions(self, transactions):
        """
        Analyze historical transactions.

        Each transaction may contain:
        {
            "amount": 5000,
            "risk_level": "LOW",
            "status": "SUCCESS",
            "policy_result": "APPROVED"
        }
        """

        if not transactions:
            return {
                "total_transactions": 0,
                "low_risk": 0,
                "medium_risk": 0,
                "high_risk": 0,
                "successful": 0,
                "blocked": 0,
                "average_amount": 0,
            }

        total = len(transactions)

        low_risk = sum(
            1
            for t in transactions
            if str(t.get("risk_level", "")).upper() == "LOW"
        )

        medium_risk = sum(
            1
            for t in transactions
            if str(t.get("risk_level", "")).upper() == "MEDIUM"
        )

        high_risk = sum(
            1
            for t in transactions
            if str(t.get("risk_level", "")).upper() == "HIGH"
        )

        successful = sum(
            1
            for t in transactions
            if str(t.get("status", "")).upper()
            in ["SUCCESS", "APPROVED", "COMPLETED"]
        )

        blocked = sum(
            1
            for t in transactions
            if str(t.get("status", "")).upper()
            in ["BLOCKED", "FAILED", "REJECTED"]
        )

        amounts = [
            float(t.get("amount", 0))
            for t in transactions
            if t.get("amount") is not None
        ]

        average_amount = (
            sum(amounts) / len(amounts)
            if amounts
            else 0
        )

        return {
            "total_transactions": total,
            "low_risk": low_risk,
            "medium_risk": medium_risk,
            "high_risk": high_risk,
            "successful": successful,
            "blocked": blocked,
            "average_amount": round(average_amount, 2),
        }

    def generate_proposals(self, analysis):
        """
        Generate policy recommendations based on transaction history.

        These are proposals only.
        """

        proposals = []

        total = analysis["total_transactions"]

        if total == 0:
            return proposals

        low_risk_rate = (
            analysis["low_risk"] / total
        )

        high_risk_rate = (
            analysis["high_risk"] / total
        )

        # -------------------------------------------------
        # Proposal 1: Auto-approval limit
        # -------------------------------------------------

        current_limit = self.current_policy["auto_approval_limit"]

        if low_risk_rate >= 0.90:

            suggested_limit = min(
                current_limit + 2000,
                25000,
            )

            if suggested_limit > current_limit:
                proposals.append({
                    "type": "AUTO_APPROVAL_LIMIT",
                    "current_value": current_limit,
                    "suggested_value": suggested_limit,
                    "reason": (
                        f"{round(low_risk_rate * 100)}% of historical "
                        "transactions were LOW risk."
                    ),
                    "confidence": "HIGH",
                })

        elif high_risk_rate >= 0.30:

            suggested_limit = max(
                current_limit - 2000,
                5000,
            )

            if suggested_limit < current_limit:
                proposals.append({
                    "type": "AUTO_APPROVAL_LIMIT",
                    "current_value": current_limit,
                    "suggested_value": suggested_limit,
                    "reason": (
                        f"{round(high_risk_rate * 100)}% of historical "
                        "transactions were HIGH risk."
                    ),
                    "confidence": "HIGH",
                })

        # -------------------------------------------------
        # Proposal 2: Quantity limit
        # -------------------------------------------------

        current_quantity = self.current_policy[
            "max_quantity_per_order"
        ]

        large_orders = sum(
            1
            for amount in []
        )

        if analysis["high_risk"] > analysis["low_risk"]:
            suggested_quantity = max(
                current_quantity - 1,
                1,
            )

            if suggested_quantity < current_quantity:
                proposals.append({
                    "type": "MAX_QUANTITY",
                    "current_value": current_quantity,
                    "suggested_value": suggested_quantity,
                    "reason": (
                        "Historical risk levels indicate that "
                        "stricter quantity controls may be safer."
                    ),
                    "confidence": "MEDIUM",
                })

        # -------------------------------------------------
        # Proposal 3: Daily spend limit
        # -------------------------------------------------

        current_daily_limit = self.current_policy[
            "daily_spend_limit"
        ]

        if (
            low_risk_rate >= 0.95
            and analysis["average_amount"] > 0
        ):
            suggested_daily_limit = min(
                current_daily_limit + 5000,
                50000,
            )

            if suggested_daily_limit > current_daily_limit:
                proposals.append({
                    "type": "DAILY_SPEND_LIMIT",
                    "current_value": current_daily_limit,
                    "suggested_value": suggested_daily_limit,
                    "reason": (
                        "Historical transactions show a strong "
                        "LOW-risk pattern."
                    ),
                    "confidence": "MEDIUM",
                })

        return proposals

    def create_optimization_report(self, analysis, proposals):
        """
        Create a complete optimization report.
        """

        return {
            "current_policy": self.current_policy.copy(),
            "analysis": analysis,
            "proposals": proposals,
            "requires_human_approval": bool(proposals),
            "auto_applied": False,
        }

    def approve_proposal(self, proposal):
        """
        Apply ONE proposal only after explicit human approval.

        This function represents the governance boundary.
        """

        if not proposal:
            return False

        proposal_type = proposal.get("type")
        suggested_value = proposal.get("suggested_value")

        if suggested_value is None:
            return False

        if proposal_type == "AUTO_APPROVAL_LIMIT":
            self.current_policy["auto_approval_limit"] = (
                suggested_value
            )

        elif proposal_type == "DAILY_SPEND_LIMIT":
            self.current_policy["daily_spend_limit"] = (
                suggested_value
            )

        elif proposal_type == "MAX_QUANTITY":
            self.current_policy["max_quantity_per_order"] = (
                suggested_value
            )

        else:
            return False

        return True

    def reject_proposal(self, proposal):
        """
        Reject a proposal without changing policy.
        """

        return {
            "type": proposal.get("type"),
            "status": "REJECTED",
            "policy_changed": False,
        }


def format_optimization_report(report):
    """
    Convert optimization results into a MERCHX UI report.
    """

    analysis = report["analysis"]
    proposals = report["proposals"]

    lines = [
        "🧬 MERCHX POLICY OPTIMIZATION",
        "",
        "HISTORICAL ANALYSIS",
        f"Transactions: {analysis['total_transactions']}",
        f"LOW risk: {analysis['low_risk']}",
        f"MEDIUM risk: {analysis['medium_risk']}",
        f"HIGH risk: {analysis['high_risk']}",
        f"Successful: {analysis['successful']}",
        f"Blocked: {analysis['blocked']}",
        f"Average amount: ₹{analysis['average_amount']:,.2f}",
        "",
    ]

    if not proposals:
        lines.append(
            "✅ No policy changes recommended."
        )
        return "\n".join(lines)

    lines.append("AI RECOMMENDATIONS")

    for index, proposal in enumerate(proposals, start=1):
        lines.extend([
            "",
            f"Proposal {index}: {proposal['type']}",
            f"Current: {proposal['current_value']}",
            f"Suggested: {proposal['suggested_value']}",
            f"Reason: {proposal['reason']}",
            f"Confidence: {proposal['confidence']}",
        ])

    lines.extend([
        "",
        "⚠️ HUMAN APPROVAL REQUIRED",
        "AI suggestions are NOT automatically applied.",
    ])

    return "\n".join(lines)


def get_current_policy(optimizer):
    """
    Return a copy of the active policy.
    """

    return optimizer.current_policy.copy()