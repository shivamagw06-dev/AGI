"""Feature flags for KG-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_KG_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_KG_01_ENABLED": is_enabled(),
        "llm": False,
        "scope": "single_company",
        "cross_company": False,
        "portfolio_graph": False,
    }
