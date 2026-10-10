"""Feature flags for RW-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_RW_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_RW_01_ENABLED": is_enabled(),
        "llm": False,
        "generates_recommendations": False,
        "mutates_system_intelligence": False,
        "presentation_only": True,
        "notes_are_analyst_owned": True,
    }
