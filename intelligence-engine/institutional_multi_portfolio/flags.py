"""Feature flags for MPC-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_MPC_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_MPC_01_ENABLED": is_enabled(),
        "llm": False,
        "owns_intelligence": False,
        "intelligence_is_global": True,
        "portfolios_are_local": True,
        "permissions_separate_from_data": True,
        "execution_context_explicit": True,
    }
