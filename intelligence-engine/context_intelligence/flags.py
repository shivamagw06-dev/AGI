"""CIE feature flags — Intent Intelligence soft-wire only."""

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
    return bool(getattr(s, "context_intelligence", True))


def flags_dict() -> dict[str, Any]:
    return {
        "CONTEXT_INTELLIGENCE": is_enabled(),
        "CIE_V1": True,
        "CIE_RESEARCH_CONTEXT_CARD": True,
        "CIE_DYNAMIC_PRIORITY": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
