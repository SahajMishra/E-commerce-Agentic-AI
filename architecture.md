# Autonomous Support Resolution Agent Architecture

## Overview
This system implements a production-style autonomous ticket resolution pipeline using a custom ReAct-like loop:

1. **Thought** (planner decides next step)
2. **Action** (tool execution with retry/backoff)
3. **Observation** (validated tool output stored in ticket memory)
4. Repeat until resolution decision

The runtime is fully asynchronous and processes tickets concurrently.

## Components

- `main.py`: entry point, async orchestration, bounded concurrency, dead-letter handling.
- `agent/planner.py`: ticket classification and iterative next-action planning.
- `agent/executor.py`: tool routing, retries, output validation, failure-safe execution.
- `agent/memory.py`: per-ticket state container for observations, steps, and tool trace.
- `agent/confidence.py`: confidence scoring before final action.
- `agent/agent_loop.py`: decision policy, escalation rules, and final action handling.
- `tools/read_tools.py`: read-only mock tools with latency, timeout, malformed response simulation.
- `tools/write_tools.py`: state-changing mock tools (`issue_refund`, `send_reply`, `escalate`).
- `utils/retry.py`: async exponential backoff with jitter.
- `utils/validator.py`: schema checks and confidence clamping.
- `utils/logger.py`: thread-safe structured audit logger.

## Safety and Reliability Controls

- Minimum three tool calls per ticket for complete traceability.
- Explicit validation before acting on tool outputs.
- Retry with exponential backoff for timeout/malformed conditions.
- Confidence threshold (`< 0.6`) triggers forced escalation.
- Refund guardrail: refund path only executes after `check_refund_eligibility`.
- Irreversible operation (`issue_refund`) isolated and explicitly audited.
- Graceful failure: ticket-level isolation + dead-letter queue.

## Concurrency Model

- Uses an explicit async queue + worker-pool (`N` workers, default `6`).
- Each worker continuously pulls tickets and processes them independently.
- Shared resources (`audit log`, `dead-letter`) protected with async locks.
- Audit records store `worker_id` for runtime traceability.
- Individual ticket failures do not crash global execution.

## Observability

Each audit record includes:
- Classification
- ReAct steps taken
- Every tool call input/output + success/failure
- Reasoning summary
- Final decision
- Confidence score
