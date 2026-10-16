"""Feature flags for Institutional Reasoning soft policy."""

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
    if settings is None:
        return True
    return bool(getattr(settings, "institutional_reasoning", True)) and bool(
        getattr(settings, "ask_agi_institutional_reasoning", True)
    )


def flags_dict() -> dict[str, Any]:
    return {
        "INSTITUTIONAL_REASONING": is_enabled(),
        "ASK_AGI_INSTITUTIONAL_REASONING": is_enabled(),
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
        "REASONING_QUALITY_POLICY": True,
        "EVIDENCE_BEFORE_ANSWER": True,
    }
