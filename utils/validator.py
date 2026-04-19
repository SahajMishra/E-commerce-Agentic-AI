from typing import Any, Dict


class ValidationError(Exception):
    pass


def require_keys(payload: Dict[str, Any], keys: list[str], context: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError(f"{context}: response is not a dict")
    missing = [k for k in keys if k not in payload or payload[k] is None]
    if missing:
        raise ValidationError(f"{context}: missing keys {missing}")
    return payload


def clamp_confidence(score: float) -> float:
    return max(0.0, min(1.0, round(score, 3)))
