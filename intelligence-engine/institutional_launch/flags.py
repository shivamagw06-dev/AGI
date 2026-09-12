"""Feature flags for L-01 launch instrumentation (not v1.1 product flags)."""

from __future__ import annotations

import os
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_enabled() -> bool:
    return _truthy("AGI_L_01_ENABLED", "true")


def journey_tracking_enabled() -> bool:
    return _truthy("AGI_L_01_JOURNEY", "true")


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_L_01_ENABLED": is_enabled(),
        "AGI_L_01_JOURNEY": journey_tracking_enabled(),
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "is_feature_expansion": False,
        "is_usage_validation": True,
        "guiding_principle": (
            "Validate that AGIB solves real analyst workflows before expanding the product."
        ),
    }
