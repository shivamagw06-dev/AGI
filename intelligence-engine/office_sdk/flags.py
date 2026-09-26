"""Feature flags for Office SDK."""

from __future__ import annotations

import os
from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name.upper()) or os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    return _flag("OFFICE_SDK", True)


def flags_dict() -> dict[str, Any]:
    return {"OFFICE_SDK": is_enabled()}
