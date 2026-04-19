import asyncio
from typing import Any, Dict, List, Optional


class ProgressTracker:
    """Thread-safe (asyncio) progress state for the web UI."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.running = False
        self.total = 0
        self.completed = 0
        self.failed = 0
        self.events: List[Dict[str, Any]] = []

    async def start_run(self, total: int) -> None:
        async with self._lock:
            self.running = True
            self.total = total
            self.completed = 0
            self.failed = 0
            self.events = [{"type": "run_started", "total": total}]

    async def ticket_started(self, ticket_id: str, worker_id: int) -> None:
        async with self._lock:
            self._append({"type": "ticket_started", "ticket_id": ticket_id, "worker_id": worker_id})

    async def ticket_finished(self, ticket_id: str, success: bool, summary: str) -> None:
        async with self._lock:
            self.completed += 1
            if not success:
                self.failed += 1
            self._append(
                {
                    "type": "ticket_finished",
                    "ticket_id": ticket_id,
                    "success": success,
                    "summary": summary,
                }
            )

    async def ticket_error(self, ticket_id: str, reason: str) -> None:
        async with self._lock:
            self.completed += 1
            self.failed += 1
            self._append({"type": "ticket_error", "ticket_id": ticket_id, "reason": reason})

    async def run_finished(self) -> None:
        async with self._lock:
            self.running = False
            self._append({"type": "run_finished"})

    async def run_failed(self, reason: str) -> None:
        async with self._lock:
            self.running = False
            self._append({"type": "run_error", "reason": reason})

    async def snapshot(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "running": self.running,
                "total": self.total,
                "completed": self.completed,
                "failed": self.failed,
                "events": list(self.events),
            }

    def _append(self, evt: Dict[str, Any]) -> None:
        self.events.append(evt)
        if len(self.events) > 200:
            self.events = self.events[-200:]
