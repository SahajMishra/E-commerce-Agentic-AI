from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCallRecord:
    name: str
    inputs: Dict[str, Any]
    output: Dict[str, Any]
    success: bool
    error: Optional[str] = None


@dataclass
class TicketState:
    ticket: Dict[str, Any]
    classification: Dict[str, Any] = field(default_factory=dict)
    observations: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, str]] = field(default_factory=list)
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    final_decision: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    retries: int = 0
    failed: bool = False
    dead_letter_reason: Optional[str] = None

    def add_step(self, thought: str, action: str, observation: str) -> None:
        self.steps.append({"thought": thought, "action": action, "observation": observation})
