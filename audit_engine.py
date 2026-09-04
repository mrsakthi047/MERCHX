# MERCHX Audit Engine
# Records important commerce decisions and creates a tamper-evident
# hash chain for audit integrity.

import hashlib
import json
from datetime import datetime, timezone


class AuditEngine:
    def __init__(self):
        self.events = []
        self.last_hash = "GENESIS"

    def _create_hash(self, event_data, previous_hash):
        payload = {
            "event": event_data,
            "previous_hash": previous_hash,
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            default=str,
        ).encode("utf-8")

        return hashlib.sha256(serialized).hexdigest()

    def record_event(
        self,
        action,
        agent_id="UNKNOWN",
        product_id=None,
        amount=0,
        decision=None,
        risk_level=None,
        policy_status=None,
        payment_status=None,
        metadata=None,
    ):
        """
        Record one MERCHX event in the audit chain.
        """

        event = {
            "audit_id": f"MX-AUD-{len(self.events) + 1:06d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "agent_id": agent_id,
            "product_id": product_id,
            "amount": amount,
            "decision": decision,
            "risk_level": risk_level,
            "policy_status": policy_status,
            "payment_status": payment_status,
            "metadata": metadata or {},
        }

        event_hash = self._create_hash(
            event,
            self.last_hash,
        )

        event["previous_hash"] = self.last_hash
        event["event_hash"] = event_hash

        self.events.append(event)
        self.last_hash = event_hash

        return event

    def get_events(self):
        """
        Return all audit events.
        """

        return self.events

    def get_latest_event(self):
        """
        Return the most recent audit event.
        """

        if not self.events:
            return None

        return self.events[-1]

    def verify_integrity(self):
        """
        Verify that the audit hash chain has not been altered.
        """

        previous_hash = "GENESIS"

        for event in self.events:
            stored_hash = event.get("event_hash")

            event_without_hash = {
                key: value
                for key, value in event.items()
                if key != "event_hash"
            }

            # The hash was originally calculated using the event
            # before previous_hash and event_hash were attached.
            original_event = {
                key: value
                for key, value in event_without_hash.items()
                if key != "previous_hash"
            }

            calculated_hash = self._create_hash(
                original_event,
                previous_hash,
            )

            if event.get("previous_hash") != previous_hash:
                return False

            if stored_hash != calculated_hash:
                return False

            previous_hash = stored_hash

        return True

    def clear(self):
        """
        Clear the in-memory audit trail.
        """

        self.events = []
        self.last_hash = "GENESIS"


def create_audit_summary(audit_event):
    """
    Create a compact human-readable audit summary.
    """

    if not audit_event:
        return "No audit event available."

    return (
        f"📋 AUDIT ID: {audit_event['audit_id']}\n"
        f"Action: {audit_event['action']}\n"
        f"Agent: {audit_event['agent_id']}\n"
        f"Product: {audit_event['product_id'] or 'N/A'}\n"
        f"Amount: ₹{audit_event['amount']:,}\n"
        f"Policy: {audit_event['policy_status'] or 'N/A'}\n"
        f"Risk: {audit_event['risk_level'] or 'N/A'}\n"
        f"Decision: {audit_event['decision'] or 'N/A'}\n"
        f"Payment: {audit_event['payment_status'] or 'N/A'}"
    )


def export_audit_log(audit_engine):
    """
    Export the audit trail as JSON.
    """

    return json.dumps(
        audit_engine.get_events(),
        indent=2,
        default=str,
    )