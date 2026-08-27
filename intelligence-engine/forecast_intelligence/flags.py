"""FIE feature flags — soft layer only."""

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
    return bool(getattr(s, "forecast_intelligence", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "forecast_intelligence", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "FORECAST_INTELLIGENCE": is_enabled(),
        "FIE_SCENARIOS": _sub("fie_scenarios"),
        "FIE_CATALYSTS": _sub("fie_catalysts"),
        "FIE_TRIGGERS": _sub("fie_triggers"),
        "FIE_SENSITIVITY": _sub("fie_sensitivity"),
        "FIE_EXPECTATIONS": _sub("fie_expectations"),
        "FIE_CONSENSUS": _sub("fie_consensus"),
        "FIE_UNCERTAINTY": _sub("fie_uncertainty"),
        "FIE_PROBABILITY": _sub("fie_probability"),
    }
