# Failure Modes and Mitigations

## 1) Tool Timeout During Eligibility Check
- **Scenario:** `check_refund_eligibility(order_id)` times out under load.
- **Risk:** Refund decision made without policy verification.
- **Mitigation:** `retry_async` retries up to 3 times with exponential backoff + jitter.
- **Fallback:** If still failing, agent escalates with high priority and includes attempted checks in summary.

## 2) Malformed or Partial Tool Response
- **Scenario:** `get_order` or `get_customer` returns malformed payload/missing required keys.
- **Risk:** Incorrect autonomous action due to bad data.
- **Mitigation:** Output schema validation in `ToolExecutor._validate`.
- **Fallback:** Failed validation is treated as tool failure; agent continues with safe response or escalation.

## 3) Irreversible Refund Action Risk
- **Scenario:** False-positive refund approval due to weak evidence.
- **Risk:** Financial loss; irreversible write operation.
- **Mitigation:** Hard rule that refund is only possible after successful `check_refund_eligibility`.
- **Fallback:** If uncertainty remains (confidence < 0.6 or amount > $200), escalate instead of refund.

## 4) End-to-End Ticket Processing Failure
- **Scenario:** Unexpected exception bubbles from agent loop.
- **Risk:** Pipeline crash or dropped tickets.
- **Mitigation:** Per-ticket exception isolation in `process_one`.
- **Fallback:** Ticket is written to `outputs/dead_letter.json` with failure reason for reprocessing.
