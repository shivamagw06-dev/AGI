"""IAPE feature flags — Intent Intelligence soft-wire only."""

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
    return bool(getattr(s, "acquisition_planner", True))


def flags_dict() -> dict[str, Any]:
    return {
        "ACQUISITION_PLANNER": is_enabled(),
        "IAPE_V1": True,
        "IAPE_EVIDENCE_BUDGET": True,
        "IAPE_INTERNAL_REUSE_FIRST": True,
        "IAPE_NO_DUPLICATE_FETCH": True,
        "IAPE_TIER1_PREFERRED": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
