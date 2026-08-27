"""E2E-01 feature flags."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = str(os.environ.get("AGI_E2E_01_ENABLED", "1")).strip().lower()
    return raw not in {"0", "false", "off", "no"}


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_E2E_01_ENABLED": is_enabled(),
        "role": "product_experience_validation",
    }
