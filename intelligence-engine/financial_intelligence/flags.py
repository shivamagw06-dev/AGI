"""FIRE-01 feature flags."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    return str(os.getenv("FIRE_ENABLED", "true")).strip().lower() in {"1", "true", "yes", "on"}


def flags_dict() -> dict[str, Any]:
    return {
        "FIRE_ENABLED": is_enabled(),
        "reads_warehouse_only": True,
        "mutates_warehouse": False,
        "uses_llm": False,
        "issues_recommendations": False,
    }
