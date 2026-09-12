"""ILM feature flags — soft layer only."""

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
    return bool(getattr(s, "institutional_memory", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "institutional_memory", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "INSTITUTIONAL_MEMORY": is_enabled(),
        "ILM_THESIS": _sub("ilm_thesis"),
        "ILM_ANALYST": _sub("ilm_analyst"),
        "ILM_COMMITTEE": _sub("ilm_committee"),
        "ILM_FORECAST": _sub("ilm_forecast"),
        "ILM_PORTFOLIO": _sub("ilm_portfolio"),
        "ILM_LEARNING": _sub("ilm_learning"),
        "ILM_ACCURACY": _sub("ilm_accuracy"),
        "ILM_MISTAKE_INTELLIGENCE": _sub("ilm_mistake_intelligence"),
    }
