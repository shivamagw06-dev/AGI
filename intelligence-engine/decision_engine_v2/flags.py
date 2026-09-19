"""IDE V2 feature flags — soft layer only; does not alter decision_engine V1."""

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
    return bool(getattr(s, "decision_engine_v2", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "decision_engine_v2", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "DECISION_ENGINE_V2": is_enabled(),
        "IDEV2_ORCHESTRATOR": _sub("idev2_orchestrator"),
        "IDEV2_CONSTITUTION": _sub("idev2_constitution"),
        "IDEV2_WEIGHTING": _sub("idev2_weighting"),
        "IDEV2_CONFLICTS": _sub("idev2_conflicts"),
        "IDEV2_UNCERTAINTY": _sub("idev2_uncertainty"),
        "IDEV2_CONFIDENCE": _sub("idev2_confidence"),
        "IDEV2_RECOMMENDATION_GATE": _sub("idev2_recommendation_gate"),
        "IDEV2_MONITORING": _sub("idev2_monitoring"),
        "IDEV2_AUDIT": _sub("idev2_audit"),
        "IDEV2_LEARNING_HOOKS": _sub("idev2_learning_hooks"),
        "ARCHITECTURE_FROZEN": True,
    }
