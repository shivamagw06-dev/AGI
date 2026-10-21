"""BBCE feature flags — soft-wire only; not a top-level intelligence layer."""

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
    return bool(getattr(s, "belief_engine", True))


def flags_dict() -> dict[str, Any]:
    return {
        "BELIEF_ENGINE": is_enabled(),
        "BBCE_V1": True,
        "BBCE_BAYESIAN_UPDATE": True,
        "BBCE_CALIBRATION": True,
        "BBCE_DRIFT_DETECTION": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_6": True,
    }
