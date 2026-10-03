"""IVCE feature flags — Intent Intelligence soft-wire only."""

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
    return bool(getattr(s, "validation_engine", True))


def flags_dict() -> dict[str, Any]:
    return {
        "VALIDATION_ENGINE": is_enabled(),
        "IVCE_V1": True,
        "IVCE_READINESS_MEMO": True,
        "IVCE_GATE_BEFORE_EXECUTION": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
    }
