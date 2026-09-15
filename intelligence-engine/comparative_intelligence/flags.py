"""Feature flags for CIO-01."""

from __future__ import annotations

import os
from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name.upper()) or os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    return _flag("COMPARATIVE_INTELLIGENCE", True) and _flag("CIO01", True)


def flags_dict() -> dict[str, Any]:
    return {
        "COMPARATIVE_INTELLIGENCE": is_enabled(),
        "CIO01": _flag("CIO01", True),
    }
