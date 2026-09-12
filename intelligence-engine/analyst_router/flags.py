"""IAR feature flags — Intent Intelligence soft-wire only."""

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
    return bool(getattr(s, "analyst_router", True))


def flags_dict() -> dict[str, Any]:
    return {
        "ANALYST_ROUTER": is_enabled(),
        "IAR_V1": True,
        "IAR_SUPPRESS_UNSELECTED": True,
        "IAR_NO_PLACEHOLDERS": True,
        "IAR_RESEARCH_ASSIGNMENTS": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
