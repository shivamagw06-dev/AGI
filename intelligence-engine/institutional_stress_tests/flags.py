"""Feature flags for IST."""

from __future__ import annotations

import os
from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name.upper()) or os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def is_enabled() -> bool:
    return _flag("INSTITUTIONAL_STRESS_TESTS", True) and (
        _flag("IST01", True) or _flag("IST02", True)
    )


def flags_dict() -> dict[str, Any]:
    return {
        "INSTITUTIONAL_STRESS_TESTS": is_enabled(),
        "IST01": _flag("IST01", True),
        "IST02": _flag("IST02", True),
    }
