"""Feature flags for IB-01 Institutional Benchmark."""

from __future__ import annotations

import os
from typing import Any


def _truthy(name: str, default: str = "true") -> bool:
    raw = (os.environ.get(name) or default).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def is_enabled() -> bool:
    return _truthy("AGI_IB_01_ENABLED", "true")


def harness_mode() -> bool:
    """Automated rubric proxies (not a marketing claim vs Bloomberg)."""
    return _truthy("AGI_IB_01_HARNESS", "true")


def require_panel_for_grade() -> bool:
    """Institutional Grade requires recorded blind + productivity panels."""
    return _truthy("AGI_IB_01_REQUIRE_PANEL", "true")


def flags_dict() -> dict[str, Any]:
    return {
        "AGI_IB_01_ENABLED": is_enabled(),
        "AGI_IB_01_HARNESS": harness_mode(),
        "AGI_IB_01_REQUIRE_PANEL": require_panel_for_grade(),
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        "is_competitive_intelligence_test": True,
        "is_software_acceptance": False,
        "distinct_from_pat": True,
        "distinct_from_ibs": True,
        "guiding_principle": (
            "PAT proves the software works. IB-01 proves the investment "
            "intelligence is competitive."
        ),
    }
