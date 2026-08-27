"""ICI feature flags — soft defaults on; orchestration only."""

from __future__ import annotations


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("investment_committee_intelligence", True) and _flag("ask_agi_ici", True)


def flags_dict() -> dict[str, bool]:
    return {
        "INVESTMENT_COMMITTEE_INTELLIGENCE": _flag("investment_committee_intelligence", True),
        "ASK_AGI_ICI": _flag("ask_agi_ici", True),
        "ICI_ENABLED": is_enabled(),
    }
