"""IHG feature flags — soft-wire only; not a top-level intelligence layer."""

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
    return bool(getattr(s, "hypothesis_engine", True))


def flags_dict() -> dict[str, Any]:
    return {
        "HYPOTHESIS_ENGINE": is_enabled(),
        "IHG_V1": True,
        "IHG_FIVE_RULES": True,
        "IHG_NO_GENERIC_HYPOTHESES": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_1": True,
    }
