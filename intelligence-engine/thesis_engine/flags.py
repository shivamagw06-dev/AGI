"""ITCE feature flags — soft-wire only; not a top-level intelligence layer."""

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
    return bool(getattr(s, "thesis_engine", True))


def flags_dict() -> dict[str, Any]:
    return {
        "THESIS_ENGINE": is_enabled(),
        "ITCE_V1": True,
        "ITCE_PILLAR_DEPENDENCIES": True,
        "ITCE_CATALYSTS": True,
        "ITCE_CONVICTION": True,
        "ITCE_INTERACTION_MATRIX": True,
        "ITCE_STABILITY": True,
        "ITCE_QUALITY_SCORE": True,
        "ITCE_THESIS_DNA": True,
        "ITCE_CONVICTION_WATERFALL": True,
        "ITCE_MONITORING": True,
        "ITCE_EVOLUTION": True,
        "ITCE_PRESSURE_GAUGE": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_7": True,
    }
