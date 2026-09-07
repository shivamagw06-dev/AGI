"""Feature flags for PAT-01 Production Acceptance Test."""

from __future__ import annotations

import os
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_enabled() -> bool:
    return _truthy("AGI_PAT_01_ENABLED", "true")


def harness_mode() -> bool:
    """Deterministic acceptance harness (no live infra required). Default on."""
    return _truthy("AGI_PAT_01_HARNESS", "true")


def live_probes_enabled() -> bool:
    return _truthy("AGI_PAT_01_LIVE", "false")


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_PAT_01_ENABLED": is_enabled(),
        "AGI_PAT_01_HARNESS": harness_mode(),
        "AGI_PAT_01_LIVE": live_probes_enabled(),
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "is_production_acceptance": True,
        "is_feature_expansion": False,
        "guiding_principle": (
            "Validate that every subsystem works together under realistic conditions "
            "before onboarding users."
        ),
    }
