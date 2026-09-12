"""IDEB feature flags — structured pre-Committee debate, not a new layer."""

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
    return True if settings is None else bool(getattr(settings, "debate_engine", True))


def flags_dict() -> dict[str, Any]:
    return {
        "DEBATE_ENGINE": is_enabled(),
        "IDEB_V1": True,
        "IDEB_CHALLENGE_TOURNAMENT": True,
        "IDEB_DEBATE_SCORECARD": True,
        "IDEB_MINORITY_PRESERVATION": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "NOT_ANOTHER_COMMITTEE": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_8": True,
    }
