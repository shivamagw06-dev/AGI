"""Feature flags for Intelligence Construction V2 — soft defaults on."""

from __future__ import annotations


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        s = get_settings()
        return bool(getattr(s, name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("intelligence_construction", True) and _flag("ask_agi_intelligence_v2", True)


def flags_dict() -> dict[str, bool]:
    return {
        "INTELLIGENCE_CONSTRUCTION": is_enabled(),
        "ASK_AGI_INTELLIGENCE_V2": _flag("ask_agi_intelligence_v2", True),
    }
