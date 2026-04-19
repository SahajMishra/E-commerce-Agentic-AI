from main.agent.memory import TicketState
from main.utils.validator import clamp_confidence


class ConfidenceEvaluator:
    def evaluate(self, state: TicketState) -> float:
        base = 0.55
        successful_tools = len([t for t in state.tool_calls if t.success])
        failed_tools = len([t for t in state.tool_calls if not t.success])
        has_order = "order" in state.observations
        has_customer = "customer" in state.observations
        has_policy = "kb" in state.observations
        has_eligibility = "refund_eligibility" in state.observations

        score = base
        score += min(0.2, successful_tools * 0.03)
        score -= min(0.25, failed_tools * 0.05)
        score += 0.08 if has_order else -0.05
        score += 0.05 if has_customer else -0.05
        score += 0.03 if has_policy else 0.0
        score += 0.08 if has_eligibility else 0.0
        if state.final_decision.get("action") == "escalate":
            score += 0.03
        return clamp_confidence(score)
