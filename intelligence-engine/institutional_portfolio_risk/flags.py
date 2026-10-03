"""Feature flags for PRE-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_PRE_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_PRE_01_ENABLED": is_enabled(),
        "llm": False,
        "monte_carlo": False,
        "var": False,
        "optimises": False,
        "authoritative_for_cio": True,
    }
