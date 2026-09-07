"""Feature flags for PKG-01 Portfolio Knowledge Graph."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_PKG_01_ENABLED") or os.environ.get("AGI_PO_01_PKG_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_PKG_01_ENABLED": is_enabled(),
        "llm": False,
        "optimises": False,
        "scope": "single_portfolio",
        "company_graphs": True,
    }
