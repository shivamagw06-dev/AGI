"""FIRE-05 feature flags."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    return str(os.getenv("FIRE05_ENABLED", os.getenv("FIRE_ENABLED", "true"))).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def flags_dict() -> dict[str, Any]:
    return {
        "FIRE05_ENABLED": is_enabled(),
        "reads_fire03_fire04_warehouse": True,
        "mutates_warehouse": False,
        "uses_llm": False,
        "issues_recommendations": False,
        "judges_honesty": False,
        "fire_01_unchanged": True,
        "fire_02_unchanged": True,
        "fire_03_unchanged": True,
        "fire_04_unchanged": True,
    }
