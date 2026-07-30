"""Configuration helpers for the single-browser demonstration mode."""

import os


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def demo_local_history_enabled() -> bool:
    """Return whether demo results should stay out of durable history tables."""

    return parse_bool(os.getenv("DEMO_LOCAL_HISTORY"), default=False)
