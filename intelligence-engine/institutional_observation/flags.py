"""Feature flags for IO-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_IO_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_IO_01_ENABLED": is_enabled(),
        "llm": False,
        "predictive_alerts": False,
        "hysteresis": True,
        "proactive": True,
    }
