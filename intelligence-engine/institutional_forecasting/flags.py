"""Feature flags for FG-01."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = (os.environ.get("AGI_FG_01_ENABLED") or "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_FG_01_ENABLED": is_enabled(),
        "llm": False,
        "ml_price_prediction": False,
        "monte_carlo": False,
        "deterministic_propagation": True,
        "scope": "single_company",
    }
