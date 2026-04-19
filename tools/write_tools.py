from typing import Any, Dict

from main.tools.mocks import MockDataStore, maybe_malformed, maybe_timeout, simulate_latency


class WriteTools:
    def __init__(self, store: MockDataStore) -> None:
        self.store = store

    async def issue_refund(self, order_id: str, amount: float) -> Dict[str, Any]:
        await simulate_latency(150, 450)
        maybe_timeout(0.12)
        malformed = maybe_malformed(0.08)
        if malformed:
            return malformed

        order = self.store.orders.get(order_id)
        if not order:
            return {"success": False, "reason": "order_not_found", "order_id": order_id}
        if order.get("refund_status") == "refunded":
            return {"success": False, "reason": "already_refunded", "order_id": order_id}

        order["refund_status"] = "refunded"
        event = {"order_id": order_id, "amount": amount, "irreversible": True}
        self.store.refunds_issued.append(event)
        return {"success": True, "refund": event}

    async def send_reply(self, ticket_id: str, message: str) -> Dict[str, Any]:
        await simulate_latency(80, 260)
        maybe_timeout(0.05)
        malformed = maybe_malformed(0.04)
        if malformed:
            return malformed
        event = {"ticket_id": ticket_id, "message": message[:500]}
        self.store.replies_sent.append(event)
        return {"success": True, "reply_id": f"RPL-{ticket_id}", "ticket_id": ticket_id}

    async def escalate(self, ticket_id: str, summary: str, priority: str) -> Dict[str, Any]:
        await simulate_latency(120, 380)
        maybe_timeout(0.07)
        malformed = maybe_malformed(0.05)
        if malformed:
            return malformed
        event = {"ticket_id": ticket_id, "summary": summary[:600], "priority": priority}
        self.store.escalations.append(event)
        return {"success": True, "escalation_id": f"ESC-{ticket_id}", "priority": priority}
