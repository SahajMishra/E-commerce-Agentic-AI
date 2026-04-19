import re
from typing import Any, Dict, Optional

from agent.memory import TicketState


class Planner:
    ORDER_PATTERN = re.compile(r"\bORD-\d{4}\b")

    def classify(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        text = (ticket.get("subject", "") + " " + ticket.get("body", "")).lower()
        category = "general"
        if any(x in text for x in ["refund", "return"]):
            category = "refund_or_return"
        if "cancel" in text:
            category = "cancellation"
        if any(x in text for x in ["damaged", "defect", "broken", "cracked"]):
            category = "damaged_or_defective"
        if "where is my order" in text or "tracking" in text:
            category = "shipping_status"

        urgency = "low"
        if any(x in text for x in ["urgent", "lawyer", "bank", "dispute", "immediately"]):
            urgency = "high"
        elif ticket.get("tier", 1) >= 2:
            urgency = "medium"

        resolvability = "unknown"
        if self.ORDER_PATTERN.search(text):
            resolvability = "likely_autonomous"
        elif "policy" in text or "process" in text:
            resolvability = "autonomous_response"
        else:
            resolvability = "needs_clarification"

        return {"category": category, "urgency": urgency, "resolvability": resolvability}

    def extract_order_id(self, ticket: Dict[str, Any]) -> Optional[str]:
        text = f"{ticket.get('subject', '')} {ticket.get('body', '')}"
        match = self.ORDER_PATTERN.search(text)
        return match.group(0) if match else None

    def next_action(self, state: TicketState) -> Dict[str, Any]:
        t = state.ticket
        if "customer" not in state.observations:
            return {"type": "tool", "tool": "get_customer", "args": {"email": t["customer_email"]}, "thought": "Verify customer profile and tier in system."}

        if "order" not in state.observations:
            order_id = self.extract_order_id(t)
            if order_id:
                return {"type": "tool", "tool": "get_order", "args": {"order_id": order_id}, "thought": "Fetch order details to validate claim."}
            return {"type": "tool", "tool": "search_knowledge_base", "args": {"query": t["subject"] + " " + t["body"]}, "thought": "No order ID found; pull policy guidance."}

        order = state.observations.get("order", {})
        if order and "product" not in state.observations:
            return {"type": "tool", "tool": "get_product", "args": {"product_id": order["product_id"]}, "thought": "Fetch product-specific policy constraints."}

        if "refund" in (t.get("subject", "") + " " + t.get("body", "")).lower() and "refund_eligibility" not in state.observations and state.observations.get("order"):
            return {
                "type": "tool",
                "tool": "check_refund_eligibility",
                "args": {"order_id": state.observations["order"]["order_id"]},
                "thought": "Policy requires eligibility check before refund.",
            }

        if "kb" not in state.observations:
            return {"type": "tool", "tool": "search_knowledge_base", "args": {"query": t["subject"]}, "thought": "Collect policy snippets for explainable response."}

        return {"type": "decide", "thought": "Sufficient evidence gathered; decide final action."}
