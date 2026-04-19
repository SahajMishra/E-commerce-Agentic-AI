import asyncio
import json
import random
from pathlib import Path
from typing import Any, Dict, Optional


class ToolTimeoutError(Exception):
    pass


class ToolMalformedResponseError(Exception):
    pass


class MockDataStore:
    def __init__(self, data_dir: str) -> None:
        base = Path(data_dir)
        with (base / "orders.json").open("r", encoding="utf-8") as f:
            orders = json.load(f)
        with (base / "customers.json").open("r", encoding="utf-8") as f:
            customers = json.load(f)
        with (base / "products.json").open("r", encoding="utf-8") as f:
            products = json.load(f)
        with (base / "knowledge-base.md").open("r", encoding="utf-8") as f:
            kb_md = f.read()

        self.orders: Dict[str, Dict[str, Any]] = {o["order_id"]: o for o in orders}
        self.customers_by_email: Dict[str, Dict[str, Any]] = {c["email"]: c for c in customers}
        self.customers_by_id: Dict[str, Dict[str, Any]] = {c["customer_id"]: c for c in customers}
        self.products: Dict[str, Dict[str, Any]] = {p["product_id"]: p for p in products}
        self.kb = [{"id": "KB-MASTER", "content": kb_md}]
        self.refunds_issued: list[Dict[str, Any]] = []
        self.replies_sent: list[Dict[str, Any]] = []
        self.escalations: list[Dict[str, Any]] = []

    def get_customer_by_email(self, email: str) -> Dict[str, Any]:
        return self.customers_by_email.get(email, {})

    def get_orders_for_email(self, email: str) -> list[Dict[str, Any]]:
        customer = self.get_customer_by_email(email)
        if not customer:
            return []
        customer_id = customer["customer_id"]
        matches = [o for o in self.orders.values() if o["customer_id"] == customer_id]
        return sorted(matches, key=lambda x: x["order_date"], reverse=True)


async def simulate_latency(min_ms: int = 80, max_ms: int = 350) -> None:
    await asyncio.sleep(random.uniform(min_ms / 1000.0, max_ms / 1000.0))


def maybe_timeout(chance: float = 0.08) -> None:
    if random.random() < chance:
        raise ToolTimeoutError("Tool call timed out")


def maybe_malformed(chance: float = 0.08) -> Optional[Dict[str, Any]]:
    if random.random() < chance:
        if random.random() < 0.5:
            return {"broken": True}
        raise ToolMalformedResponseError("Malformed response payload")
    return None
