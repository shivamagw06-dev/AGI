"""Mission Control feature flags."""

from __future__ import annotations

from typing import Any


def _flag(name: str, default: bool = True) -> bool:
    try:
        from app.core.config import get_settings

        return bool(getattr(get_settings(), name, default))
    except Exception:
        return default


def is_enabled() -> bool:
    return _flag("mission_control", True)


def flags_dict() -> dict[str, Any]:
    return {
        "MISSION_CONTROL": is_enabled(),
        "MISSION_CONTROL_APIS": is_enabled() and _flag("mission_control_apis", True),
        "MISSION_CONTROL_PLATFORMS": is_enabled() and _flag("mission_control_platforms", True),
        "MISSION_CONTROL_COVERAGE": is_enabled() and _flag("mission_control_coverage", True),
        "MISSION_CONTROL_KNOWLEDGE": is_enabled() and _flag("mission_control_knowledge", True),
        "MISSION_CONTROL_ALERTS": is_enabled() and _flag("mission_control_alerts", True),
        "MISSION_CONTROL_EVENTS": is_enabled() and _flag("mission_control_events", True),
        "MISSION_CONTROL_REPORTS": is_enabled() and _flag("mission_control_reports", True),
    }
