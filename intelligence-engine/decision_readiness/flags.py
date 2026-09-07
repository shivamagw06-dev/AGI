"""IDRE flags — final pre-Committee quality gate, no new architecture."""

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
    return True if settings is None else bool(
        getattr(settings, "decision_readiness", True)
    )


def flags_dict() -> dict[str, Any]:
    return {
        "DECISION_READINESS": is_enabled(),
        "IDRE_V1": True,
        "IDRE_DECISION_HEAT_MAP": True,
        "IDRE_GO_NO_GO_CONDITIONS": True,
        "IDRE_CAPITAL_ALLOCATION_READINESS": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "FINAL_PRE_COMMITTEE_GATE": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_9": True,
    }
