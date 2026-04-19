# Autonomous Support Resolution Agent

Production-grade hackathon project for autonomous customer support resolution with robust tool orchestration, failure handling, concurrency, and auditability.

## Features

- Custom ReAct-style loop: Thought -> Action -> Observation -> Decision
- Modular architecture (planner, executor, memory, confidence, escalation)
- Concurrent ticket processing with `asyncio`
- Mock read/write tools with realistic latency/failures
- Retry with exponential backoff + jitter
- Output validation before decision/action
- Confidence-scored decisions with escalation threshold
- Structured JSON audit logging for every ticket
- Dead-letter queue for unrecoverable processing failures
- Dockerized runtime

## Project Structure

```
.
├── main.py
├── agent/
│   ├── agent_loop.py
│   ├── planner.py
│   ├── executor.py
│   ├── memory.py
│   └── confidence.py
├── tools/
│   ├── read_tools.py
│   ├── write_tools.py
│   └── mocks.py
├── utils/
│   ├── logger.py
│   ├── retry.py
│   └── validator.py
├── data/
│   ├── tickets.json
│   ├── products.json
│   ├── orders.json
│   ├── customers.json
│   └── knowledge-base.md
├── outputs/
│   └── audit_log.json
├── failure_modes.md
├── architecture.md
├── Dockerfile
└── README.md
```


DEMO Video : https://drive.google.com/drive/u/0/folders/1RX85rhgK45ewJo4B04oJHWRocgZwaAl1


## Setup

### Local

1. Ensure Python 3.10+ installed.
2. From project root:
   ```bash
   python main.py
   ```

Optional CLI flags:

```bash
python main.py --concurrency 6 --audit-log outputs/audit_log.json --dead-letter outputs/dead_letter.json
```

### Docker

```bash
docker build -t support-agent .
docker run --rm -v ${PWD}/outputs:/app/outputs support-agent
```

## How It Works

1. Loads dataset from `data/`.
2. Processes tickets concurrently via an async worker pool (default 6 workers).
3. Runs planner-guided tool loop for each ticket.
4. Applies policy constraints and confidence threshold.
5. Issues reply/refund/escalation actions.
6. Writes full structured trace to `outputs/audit_log.json`.
7. Writes failed tickets to `outputs/dead_letter.json`.

## Key Policy Guards

- Never issue refund without successful `check_refund_eligibility`.
- Escalate tickets with confidence score below 0.6.
- Escalate refund requests above $200.
- Escalate warranty/replacement and high-risk fraud/legal signals.

## Example Output Shape

Each audit log ticket record includes:
- `ticket_id`
- `worker_id` (which worker processed the ticket)
- `classification`
- `steps_taken`
- `tool_calls` (inputs/outputs/errors)
- `reasoning_summary`
- `final_decision`
- `confidence_score`

## Notes

- This implementation is mock-tool based but structured for production extension.
- You can swap the planner logic with an LLM-backed planner by keeping the same executor and memory interfaces.
