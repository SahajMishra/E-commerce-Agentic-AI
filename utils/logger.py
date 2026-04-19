import asyncio
import json
from pathlib import Path
from typing import Any, Dict


class AuditLogger:
    def __init__(self, output_path: str, ticket_log_dir: str | None = None) -> None:
        self.output_path = Path(output_path)
        self.ticket_log_dir = Path(ticket_log_dir) if ticket_log_dir else self.output_path.parent / "ticket_log"
        self._records: list[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def log_ticket(self, record: Dict[str, Any]) -> None:
        async with self._lock:
            self._records.append(record)
            self._write_ticket_thought_log(record)

    async def flush(self) -> None:
        async with self._lock:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("w", encoding="utf-8") as f:
                json.dump(self._records, f, indent=2)

    @property
    def records(self) -> list[Dict[str, Any]]:
        return self._records

    def _write_ticket_thought_log(self, record: Dict[str, Any]) -> None:
        ticket_id = str(record.get("ticket_id", "unknown_ticket"))
        steps = record.get("steps_taken", []) or []
        lines = [f"Ticket: {ticket_id}", ""]
        for idx, step in enumerate(steps, start=1):
            thought = str(step.get("thought", "")).strip()
            action = str(step.get("action", "")).strip()
            observation = str(step.get("observation", "")).strip()
            lines.append(f"{idx}. thought: {thought}")
            if action:
                lines.append(f"   action: {action}")
            if observation:
                lines.append(f"   observation: {observation}")
            lines.append("")

        if not steps:
            lines.append("No thought steps recorded.")

        self.ticket_log_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.ticket_log_dir / f"{ticket_id}.txt"
        out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
