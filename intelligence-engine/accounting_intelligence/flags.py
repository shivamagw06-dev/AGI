"""ACI feature flags — soft layer only."""

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
    return bool(getattr(s, "accounting_intelligence", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "accounting_intelligence", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "ACCOUNTING_INTELLIGENCE": is_enabled(),
        "ACI_EARNINGS": _sub("aci_earnings"),
        "ACI_CASH": _sub("aci_cash"),
        "ACI_ACCRUALS": _sub("aci_accruals"),
        "ACI_FORENSICS": _sub("aci_forensics"),
        "ACI_REVENUE": _sub("aci_revenue"),
        "ACI_WORKING_CAPITAL": _sub("aci_working_capital"),
        "ACI_BALANCE_SHEET": _sub("aci_balance_sheet"),
        "ACI_POLICIES": _sub("aci_policies"),
        "ACI_BEHAVIOUR": _sub("aci_behaviour"),
    }
