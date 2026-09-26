"""FIRE-03 feature flags."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    return str(os.getenv("FIRE03_ENABLED", os.getenv("FIRE_ENABLED", "true"))).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def flags_dict() -> dict[str, Any]:
    return {
        "FIRE03_ENABLED": is_enabled(),
        "reads_idi_only": True,
        "mutates_warehouse": False,
        "mutates_idi": False,
        "uses_llm": False,
        "issues_recommendations": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
    }
