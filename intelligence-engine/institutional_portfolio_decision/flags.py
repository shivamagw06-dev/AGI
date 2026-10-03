"""Feature flags for CIO-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_CIO_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_CIO_01_ENABLED": is_enabled(),
        "llm": False,
        "mutates_company_decisions": False,
        "optimises": False,
        "executes_trades": False,
        "referential_company_decisions": True,
    }
