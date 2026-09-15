"""ILR feature flags — Intent Intelligence soft-wire only."""

from __future__ import annotations

from typing import Any


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:
        return None


def is_enabled() -> bool:
    s = _settings()
    if s is None:
        return True
    return bool(getattr(s, "layer_router", True))


def flags_dict() -> dict[str, Any]:
    return {
        "LAYER_ROUTER": is_enabled(),
        "ILR_V1": True,
        "ILR_NO_AUTOMATIC_EXECUTION": True,
        "ILR_EXPECTED_CONTRIBUTION": True,
        "ILR_SUPPRESS_BELOW_THRESHOLD": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
