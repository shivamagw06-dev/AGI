"""Feature flags for Contradiction Reasoning soft layer."""

from __future__ import annotations

from typing import Any


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:
        return None


def is_enabled() -> bool:
    settings = _settings()
    if settings is None:
        return True
    return bool(getattr(settings, "contradiction_reasoning", True)) and bool(
        getattr(settings, "ask_agi_contradiction_reasoning", True)
    )


def flags_dict() -> dict[str, Any]:
    return {
        "CONTRADICTION_REASONING": is_enabled(),
        "ASK_AGI_CONTRADICTION_REASONING": is_enabled(),
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "NOT_CONTINUOUS_RESEARCH_EVALUATION": True,
        "ARCHITECTURE_FROZEN": True,
        "REASONING_QUALITY_IMPROVEMENT": True,
    }
