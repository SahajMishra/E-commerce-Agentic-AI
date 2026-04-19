from typing import Any, Callable, Dict

from main.agent.memory import TicketState, ToolCallRecord
from main.tools.mocks import ToolMalformedResponseError, ToolTimeoutError
from main.tools.read_tools import ReadTools
from main.tools.write_tools import WriteTools
from main.utils.retry import RetryError, retry_async
from main.utils.validator import ValidationError, require_keys


class ToolExecutor:
    def __init__(self, read_tools: ReadTools, write_tools: WriteTools) -> None:
        self.read_tools = read_tools
        self.write_tools = write_tools

    def _resolver(self, tool_name: str) -> Callable[..., Any]:
        namespace = self.read_tools if hasattr(self.read_tools, tool_name) else self.write_tools
        return getattr(namespace, tool_name)

    async def run_tool(self, state: TicketState, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        fn = self._resolver(tool_name)
        try:
            output = await retry_async(
                fn,
                **args,
                retries=3,
                base_delay=0.15,
                retriable_exceptions=(ToolTimeoutError, ToolMalformedResponseError, ValidationError),
            )
            self._validate(tool_name, output)
            state.tool_calls.append(ToolCallRecord(name=tool_name, inputs=args, output=output, success=True))
            return output
        except (RetryError, ValidationError, Exception) as exc:
            state.retries += 1
            error_payload = {"error": str(exc), "tool": tool_name}
            state.tool_calls.append(
                ToolCallRecord(name=tool_name, inputs=args, output=error_payload, success=False, error=str(exc))
            )
            return error_payload

    def _validate(self, tool_name: str, output: Dict[str, Any]) -> None:
        if "error" in output:
            raise ValidationError(f"{tool_name}: returned error payload")
        required = {
            "get_order": ["order_id", "product_id", "status"],
            "check_refund_eligibility": ["order_id", "eligible", "reason"],
            "get_customer": ["customer_id", "tier", "email"],
            "get_product": ["product_id", "name", "return_window_days"],
            "search_knowledge_base": ["results"],
            "issue_refund": ["success"],
            "send_reply": ["success", "ticket_id"],
            "escalate": ["success", "priority"],
        }
        if tool_name in required:
            require_keys(output, required[tool_name], tool_name)
