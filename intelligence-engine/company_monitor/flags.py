"""CMS feature flags."""

from __future__ import annotations

from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("company_monitor", True)


def flag_auto_pipeline() -> bool:
    return is_enabled() and _flag("cms_auto_pipeline", True)


def flag_ask_agi() -> bool:
    return is_enabled() and _flag("cms_ask_agi", True)


def flag_research_writer() -> bool:
    return is_enabled() and _flag("cms_research_writer", True)


def flag_house_view_hints() -> bool:
    return is_enabled() and _flag("cms_house_view_hints", True)


def flags_dict() -> dict[str, Any]:
    return {
        "COMPANY_MONITOR": is_enabled(),
        "CMS_AUTO_PIPELINE": flag_auto_pipeline(),
        "CMS_ASK_AGI": flag_ask_agi(),
        "CMS_RESEARCH_WRITER": flag_research_writer(),
        "CMS_HOUSE_VIEW_HINTS": flag_house_view_hints(),
    }
