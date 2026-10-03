"""Feature flags for AGIB Investment Decision Engine — soft defaults on."""

from __future__ import annotations


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("decision_engine", True) and _flag("ask_agi_decision_engine", True)


def flags_dict() -> dict[str, bool]:
    return {
        "DECISION_ENGINE": is_enabled(),
        "ASK_AGI_DECISION_ENGINE": _flag("ask_agi_decision_engine", True),
    }
