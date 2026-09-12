"""Feature flags for RC-01."""

from __future__ import annotations

import os
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_enabled() -> bool:
    return _truthy("AGI_RC_01_ENABLED", "true")


def fail_on_violation() -> bool:
    """CI mode — CLI exits non-zero when violations found."""
    return _truthy("AGI_RC_01_FAIL_ON_VIOLATION", "true")


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_RC_01_ENABLED": is_enabled(),
        "AGI_RC_01_FAIL_ON_VIOLATION": fail_on_violation(),
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "is_feature": False,
        "is_quality_gate": True,
    }
