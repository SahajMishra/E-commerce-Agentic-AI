from __future__ import annotations

import asyncio
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from main.agent.memory import TicketState


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


class GeminiReasoner:
    """
    Uses Gemini for *reasoning text only* and a refund safety double-check.

    Tool selection/calling remains rule-based; Gemini never executes tools.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def think_for_step(self, state: TicketState, tool: str, args: Dict[str, Any], default: str) -> str:
        if not self.enabled:
            return default
        prompt = self._step_prompt(state, tool, args)
        text = await self._generate_text(prompt)
        text = (text or "").strip()
        return text[:260] if text else default

    async def double_check_refund(self, state: TicketState) -> Tuple[bool, str]:
        """
        Returns (approve, reason). If Gemini is not configured, defaults to approve.
        """
        if not self.enabled:
            return True, "Gemini disabled; skipped double-check."

        prompt = self._refund_prompt(state)
        text = await self._generate_text(prompt)
        approve, reason = self._parse_refund_json(text)
        return approve, reason

    def _endpoint(self) -> str:
        # REST endpoint for Generative Language API (key via query param).
        base = "https://generativelanguage.googleapis.com/v1beta"
        return f"{base}/models/{urllib.parse.quote(self.model)}:generateContent?key={urllib.parse.quote(self.api_key)}"

    async def _generate_text(self, prompt: str) -> str:
        return await asyncio.to_thread(self._generate_text_sync, prompt)

    def _generate_text_sync(self, prompt: str) -> str:
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 220,
            },
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._endpoint(),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            return f"(Gemini error: {exc})"

        try:
            payload = json.loads(raw)
            # candidates[0].content.parts[0].text
            return (
                payload.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
        except Exception:
            return ""

    def _step_prompt(self, state: TicketState, tool: str, args: Dict[str, Any]) -> str:
        t = state.ticket
        return (
            "You are writing the agent's internal 'thought' for a customer support automation run.\n"
            "IMPORTANT:\n"
            "- Do NOT suggest different tools.\n"
            "- Do NOT include secrets.\n"
            "- 1 short sentence only.\n\n"
            f"Ticket subject: {t.get('subject','')}\n"
            f"Ticket body: {t.get('body','')}\n"
            f"Planned tool call (already decided): {tool}\n"
            f"Args: {json.dumps(args, ensure_ascii=False)}\n"
            f"Known observations keys: {sorted(state.observations.keys())}\n"
        )

    def _refund_prompt(self, state: TicketState) -> str:
        t = state.ticket
        order = state.observations.get("order", {})
        customer = state.observations.get("customer", {})
        elig = state.observations.get("refund_eligibility", {})
        return (
            "You are a safety checker for issuing a refund.\n"
            "Return ONLY valid JSON with keys: approve (boolean), reason (string).\n"
            "Approve only if refund eligibility is true and there are no red flags.\n\n"
            f"Ticket: {t.get('subject','')} | {t.get('body','')}\n"
            f"Customer: {json.dumps(customer, ensure_ascii=False)}\n"
            f"Order: {json.dumps(order, ensure_ascii=False)}\n"
            f"RefundEligibility: {json.dumps(elig, ensure_ascii=False)}\n"
        )

    def _parse_refund_json(self, text: str) -> Tuple[bool, str]:
        text = (text or "").strip()
        m = _JSON_BLOCK.search(text)
        if not m:
            return False, f"Could not parse JSON from Gemini: {text[:120]}"
        try:
            obj = json.loads(m.group(0))
            approve = bool(obj.get("approve", False))
            reason = str(obj.get("reason", "")).strip() or "No reason provided."
            return approve, reason[:240]
        except Exception:
            return False, f"Invalid JSON from Gemini: {text[:120]}"

