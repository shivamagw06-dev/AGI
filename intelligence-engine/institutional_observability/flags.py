"""Feature flags for PRP-03."""

from __future__ import annotations

import os
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_enabled() -> bool:
    return _truthy("AGI_PRP_03_ENABLED", "true")


def alerts_enabled() -> bool:
    return _truthy("AGI_PRP_03_ALERTS", "true")


def middleware_enabled() -> bool:
    return _truthy("AGI_PRP_03_MIDDLEWARE", "true")


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_PRP_03_ENABLED": is_enabled(),
        "AGI_PRP_03_ALERTS": alerts_enabled(),
        "AGI_PRP_03_MIDDLEWARE": middleware_enabled(),
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "changes_platform_behavior": False,
        "enters_intelligence_layer": False,
        "guiding_principle": (
            "Observability explains how the platform behaves. "
            "It never changes platform behavior."
        ),
    }
