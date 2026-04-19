import asyncio
import json
from pathlib import Path
from typing import Any, Dict


class AuditLogger:
    def __init__(self, output_path: str) -> None:
        self.output_path = Path(output_path)
        self._records: list[Dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def log_ticket(self, record: Dict[str, Any]) -> None:
        async with self._lock:
            self._records.append(record)

    async def flush(self) -> None:
        async with self._lock:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with self.output_path.open("w", encoding="utf-8") as f:
                json.dump(self._records, f, indent=2)

    @property
    def records(self) -> list[Dict[str, Any]]:
        return self._records
