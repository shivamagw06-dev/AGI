"""Feature flags for PO-01."""

from __future__ import annotations

import os
from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name.upper()) or os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    return _flag("PORTFOLIO_OFFICE", True) and _flag("PO01", True)


def flags_dict() -> dict[str, Any]:
    return {"PORTFOLIO_OFFICE": is_enabled(), "PO01": _flag("PO01", True)}
