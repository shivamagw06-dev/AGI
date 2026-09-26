"""ROE feature flags — Intent Intelligence soft-wire only."""

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
    return bool(getattr(s, "research_objective", True))


def flags_dict() -> dict[str, Any]:
    return {
        "RESEARCH_OBJECTIVE": is_enabled(),
        "ROE_V1": True,
        "ROE_EXACTLY_ONE_PRIMARY": True,
        "ROE_CLARIFY_BELOW_85": True,
        "ROE_PLAN_BEFORE_LAYERS": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
