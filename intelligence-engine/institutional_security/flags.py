"""Feature flags for PRP-02."""

from __future__ import annotations

import os
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_enabled() -> bool:
    return _truthy("AGI_PRP_02_ENABLED", "true")


def enforce_auth() -> bool:
    """When false, gateway soft-allows anonymous demo traffic (dev only)."""
    return _truthy("AGI_PRP_02_ENFORCE", "false")


def audit_required_for_privileged() -> bool:
    return _truthy("AGI_PRP_02_AUDIT_REQUIRED", "true")


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_PRP_02_ENABLED": is_enabled(),
        "AGI_PRP_02_ENFORCE": enforce_auth(),
        "AGI_PRP_02_AUDIT_REQUIRED": audit_required_for_privileged(),
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "enters_intelligence_layer": False,
        "guiding_principle": (
            "Security decides who can perform an operation. "
            "Intelligence decides what the operation means."
        ),
    }
