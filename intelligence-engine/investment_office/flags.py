"""Investment Office feature flags."""

from __future__ import annotations

from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("investment_office", True)


def flag_morning_brief() -> bool:
    return is_enabled() and _flag("io_morning_brief", True)


def flag_analyst_queue() -> bool:
    return is_enabled() and _flag("io_analyst_queue", True)


def flag_research_queue() -> bool:
    return is_enabled() and _flag("io_research_queue", True)


def flag_coverage() -> bool:
    return is_enabled() and _flag("io_coverage", True)


def flag_risk_center() -> bool:
    return is_enabled() and _flag("io_risk_center", True)


def flag_executive_copilot() -> bool:
    return is_enabled() and _flag("io_executive_copilot", True)


def flags_dict() -> dict[str, Any]:
    return {
        "INVESTMENT_OFFICE": is_enabled(),
        "IO_MORNING_BRIEF": flag_morning_brief(),
        "IO_ANALYST_QUEUE": flag_analyst_queue(),
        "IO_RESEARCH_QUEUE": flag_research_queue(),
        "IO_COVERAGE": flag_coverage(),
        "IO_RISK_CENTER": flag_risk_center(),
        "IO_EXECUTIVE_COPILOT": flag_executive_copilot(),
    }
