"""Feature flags for IDS-02."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_IDS_02_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_IDS_02_ENABLED": is_enabled(),
        "llm": False,
        "confidence_computed": True,
        "manual_confidence_forbidden": True,
    }
