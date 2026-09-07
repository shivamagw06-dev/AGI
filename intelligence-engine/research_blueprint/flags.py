"""DRBE feature flags — Intent Intelligence soft-wire only."""

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
    return bool(getattr(s, "research_blueprint", True))


def flags_dict() -> dict[str, Any]:
    return {
        "RESEARCH_BLUEPRINT": is_enabled(),
        "DRBE_V1": True,
        "DRBE_ASSIGNMENT_BOOK": True,
        "DRBE_QUESTION_SPECIFIC_REPORTS": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
