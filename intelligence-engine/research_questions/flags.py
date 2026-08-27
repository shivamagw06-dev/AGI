"""IRQ feature flags — soft-wire only; not a top-level intelligence layer."""

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
    return bool(getattr(s, "research_questions", True))


def flags_dict() -> dict[str, Any]:
    return {
        "RESEARCH_QUESTIONS": is_enabled(),
        "IRQ_V1": True,
        "IRQ_QUESTION_TREE": True,
        "IRQ_DECISION_IMPACT": True,
        "IRQ_NO_GENERIC_QUESTIONS": True,
        "NOT_A_TOP_LEVEL_INTELLIGENCE_LAYER": True,
        "ARCHITECTURE_FROZEN": True,
        "RQ2_SPRINT_2": True,
    }
