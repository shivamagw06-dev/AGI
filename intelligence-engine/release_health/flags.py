"""RH-01 flags."""

from __future__ import annotations

import os
from typing import Any


def is_enabled() -> bool:
    raw = str(os.environ.get("AGI_RH_01_ENABLED", "1")).strip().lower()
    return raw not in {"0", "false", "off", "no"}


def flags_dict() -> dict[str, Any]:
    return {"AGI_RH_01_ENABLED": is_enabled()}
