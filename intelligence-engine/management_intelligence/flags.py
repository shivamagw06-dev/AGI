"""MII feature flags — soft layer only."""

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
    return bool(getattr(s, "management_intelligence", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "management_intelligence", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "MANAGEMENT_INTELLIGENCE": is_enabled(),
        "MII_CREDIBILITY": _sub("mii_credibility"),
        "MII_GUIDANCE": _sub("mii_guidance"),
        "MII_EXECUTION": _sub("mii_execution"),
        "MII_CAPITAL_ALLOCATION": _sub("mii_capital_allocation"),
        "MII_GOVERNANCE": _sub("mii_governance"),
        "MII_COMMUNICATION": _sub("mii_communication"),
        "MII_INCENTIVES": _sub("mii_incentives"),
        "MII_SUCCESSION": _sub("mii_succession"),
    }
