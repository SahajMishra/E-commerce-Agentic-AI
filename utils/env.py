from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    """
    Load environment variables from `env/.env` (preferred) or `.env` (fallback).
    """

    root = Path(__file__).resolve().parents[1]  # .../main
    env_dir = root / "env"
    preferred = env_dir / ".env"
    fallback = root / ".env"

    if preferred.exists():
        load_dotenv(preferred)
        return
    if fallback.exists():
        load_dotenv(fallback)

