"""Feature flags for Answer Construction V3 — soft defaults on."""

from __future__ import annotations


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("answer_construction_v3", True) and _flag("ask_agi_answer_construction_v3", True)


def flags_dict() -> dict[str, bool]:
    return {
        "ANSWER_CONSTRUCTION_V3": is_enabled(),
        "ASK_AGI_ANSWER_CONSTRUCTION_V3": _flag("ask_agi_answer_construction_v3", True),
    }
