"""IRW feature flags — soft defaults on; writing layer only."""

from __future__ import annotations


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("institutional_research_writer", True) and _flag("ask_agi_irw", True)


def flags_dict() -> dict[str, bool]:
    return {
        "INSTITUTIONAL_RESEARCH_WRITER": _flag("institutional_research_writer", True),
        "ASK_AGI_IRW": _flag("ask_agi_irw", True),
        "IRW_ENABLED": is_enabled(),
    }
