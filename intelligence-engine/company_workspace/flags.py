"""Feature flags for CW-01."""

from __future__ import annotations

import os
from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name.upper()) or os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    return _flag("COMPANY_WORKSPACE", True) and _flag("CW01", True)


def flags_dict() -> dict[str, Any]:
    return {"COMPANY_WORKSPACE": is_enabled(), "CW01": _flag("CW01", True)}
