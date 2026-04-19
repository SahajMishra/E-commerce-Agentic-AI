import argparse
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from main.agent.agent_loop import SupportResolutionAgent
from main.agent.confidence import ConfidenceEvaluator
from main.agent.executor import ToolExecutor
from main.agent.planner import Planner
from main.tools.mocks import MockDataStore
from main.tools.read_tools import ReadTools
from main.tools.write_tools import WriteTools
from main.utils.logger import AuditLogger
from main.utils.progress import ProgressTracker

# Application root (the `main/` package directory), so CLI works from repo root with sibling `.venv`.
_APP_ROOT = Path(__file__).resolve().parent


def load_tickets(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def process_one(
    ticket: Dict[str, Any],
    agent: SupportResolutionAgent,
    logger: AuditLogger,
    dead_letter: list[Dict[str, Any]],
    lock: asyncio.Lock,
    worker_id: int,
    progress: Optional[ProgressTracker] = None,
) -> None:
    ticket_id = str(ticket.get("ticket_id", ""))
    if progress:
        await progress.ticket_started(ticket_id, worker_id)
    try:
        state = await agent.process_ticket(ticket)
        record = {
            "ticket_id": ticket["ticket_id"],
            "worker_id": worker_id,
            "classification": state.classification,
            "steps_taken": state.steps,
            "tool_calls": [
                {
                    "name": c.name,
                    "inputs": c.inputs,
                    "output": c.output,
                    "success": c.success,
                    "error": c.error,
                }
                for c in state.tool_calls
            ],
            "reasoning_summary": f"Processed via iterative planner with {len(state.tool_calls)} tool calls.",
            "final_decision": state.final_decision,
            "confidence_score": state.confidence,
        }
        await logger.log_ticket(record)
        if progress:
            summary = str(state.final_decision.get("action", "done"))
            await progress.ticket_finished(ticket_id, True, summary)
    except Exception as exc:
        async with lock:
            dead_letter.append({"ticket_id": ticket.get("ticket_id"), "reason": str(exc)})
        if progress:
            await progress.ticket_error(ticket_id, str(exc))


async def run(args: argparse.Namespace, progress: Optional[ProgressTracker] = None) -> None:
    base = Path(args.data_dir)
    store = MockDataStore(str(base))
    read_tools = ReadTools(store)
    write_tools = WriteTools(store)
    executor = ToolExecutor(read_tools, write_tools)
    agent = SupportResolutionAgent(Planner(), executor, ConfidenceEvaluator())
    logger = AuditLogger(args.audit_log, ticket_log_dir=args.ticket_log_dir)

    tickets = load_tickets(str(base / "tickets.json"))
    if progress:
        await progress.start_run(len(tickets))

    try:
        dead_letter: list[Dict[str, Any]] = []
        dead_letter_lock = asyncio.Lock()
        queue: asyncio.Queue = asyncio.Queue()
        for ticket in tickets:
            queue.put_nowait(ticket)

        async def worker(worker_id: int) -> None:
            while True:
                ticket = await queue.get()
                if ticket is None:
                    queue.task_done()
                    break
                await process_one(
                    ticket,
                    agent,
                    logger,
                    dead_letter,
                    dead_letter_lock,
                    worker_id=worker_id,
                    progress=progress,
                )
                queue.task_done()

        workers = [asyncio.create_task(worker(i + 1)) for i in range(args.concurrency)]
        await queue.join()
        for _ in workers:
            queue.put_nowait(None)
        await asyncio.gather(*workers, return_exceptions=True)
        await logger.flush()

        dead_letter_path = Path(args.dead_letter)
        dead_letter_path.parent.mkdir(parents=True, exist_ok=True)
        with dead_letter_path.open("w", encoding="utf-8") as f:
            json.dump(dead_letter, f, indent=2)

        print(f"Processed {len(tickets)} tickets with concurrency={args.concurrency}")
        print(f"Audit log written to {args.audit_log}")
        print(f"Dead-letter entries: {len(dead_letter)}")
    except BaseException as exc:
        if progress:
            await progress.run_failed(str(exc))
        raise
    else:
        if progress:
            await progress.run_finished()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Autonomous Support Resolution Agent")
    parser.add_argument("--data-dir", default=str(_APP_ROOT / "data"))
    parser.add_argument("--audit-log", default=str(_APP_ROOT / "outputs" / "audit_log.json"))
    parser.add_argument("--dead-letter", default=str(_APP_ROOT / "outputs" / "dead_letter.json"))
    parser.add_argument("--ticket-log-dir", default=str(_APP_ROOT / "outputs" / "ticket_log"))
    parser.add_argument("--concurrency", type=int, default=6)
    return parser


if __name__ == "__main__":
    cli_args = build_arg_parser().parse_args()
    asyncio.run(run(cli_args))
