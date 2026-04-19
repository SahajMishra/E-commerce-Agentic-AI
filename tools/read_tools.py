from datetime import datetime
from typing import Any, Dict, List

from main.tools.mocks import MockDataStore, maybe_malformed, maybe_timeout, simulate_latency


class ReadTools:
    def __init__(self, store: MockDataStore) -> None:
        self.store = store

    async def get_order(self, order_id: str) -> Dict[str, Any]:
        await simulate_latency()
        maybe_timeout(0.05)
        malformed = maybe_malformed(0.07)
        if malformed:
            return malformed
        return self.store.orders.get(order_id, {})

    async def check_refund_eligibility(self, order_id: str) -> Dict[str, Any]:
        await simulate_latency(120, 500)
        maybe_timeout(0.2)
        malformed = maybe_malformed(0.12)
        if malformed:
            return malformed
        order = self.store.orders.get(order_id)
        if not order:
            return {"order_id": order_id, "eligible": False, "reason": "order_not_found"}
        product = self.store.products.get(order["product_id"], {})
        deadline = order.get("return_deadline")
        returnable = product.get("returnable", True)
        simulated_today = datetime(2024, 3, 15)
        within_window = False
        if deadline:
            within_window = simulated_today <= datetime.strptime(deadline, "%Y-%m-%d")
        eligible = order["status"] == "delivered" and returnable and within_window and order.get("refund_status") != "refunded"
        return {
            "order_id": order_id,
            "eligible": eligible,
            "reason": "within_policy" if eligible else "outside_policy_or_non_returnable",
            "max_refund_amount": order["amount"] if eligible else 0.0,
        }

    async def get_customer(self, email: str) -> Dict[str, Any]:
        await simulate_latency()
        maybe_timeout(0.04)
        malformed = maybe_malformed(0.06)
        if malformed:
            return malformed
        return self.store.get_customer_by_email(email)

    async def get_product(self, product_id: str) -> Dict[str, Any]:
        await simulate_latency()
        maybe_timeout(0.04)
        malformed = maybe_malformed(0.05)
        if malformed:
            return malformed
        return self.store.products.get(product_id, {})

    async def search_knowledge_base(self, query: str) -> Dict[str, List[Dict[str, Any]]]:
        await simulate_latency(100, 400)
        maybe_timeout(0.07)
        malformed = maybe_malformed(0.1)
        if malformed:
            return malformed
        query_tokens = set(query.lower().split())
        scored = []
        for item in self.store.kb:
            content_tokens = set(item["content"].lower().split())
            score = len(query_tokens.intersection(content_tokens))
            if score:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return {"results": [x[1] for x in scored[:3]]}
