"""Feature flags for Company Analysis Engine.

Master: COMPANY_ANALYSIS (does not override Context Assembly `cae`).
Subflags (brief aliases): CAE_FINANCIAL, CAE_SECTOR, CAE_BUSINESS, CAE_VALUATION, CAE_INVESTMENT_THESIS.
"""

from __future__ import annotations

from typing import Any


def _settings():
    try:
        from app.core.config import get_settings

        return get_settings()
    except Exception:
        return None


def _flag(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, name, default))


def is_enabled() -> bool:
    return _flag("company_analysis", True)


def flag_financial() -> bool:
    return is_enabled() and _flag("cae_financial", True)


def flag_sector() -> bool:
    return is_enabled() and _flag("cae_sector", True)


def flag_business() -> bool:
    return is_enabled() and _flag("cae_business", True)


def flag_valuation() -> bool:
    return is_enabled() and _flag("cae_valuation", True)


def flag_investment_thesis() -> bool:
    return is_enabled() and _flag("cae_investment_thesis", True)


def flags_dict() -> dict[str, Any]:
    return {
        "COMPANY_ANALYSIS": is_enabled(),
        "CAE_FINANCIAL": flag_financial(),
        "CAE_SECTOR": flag_sector(),
        "CAE_BUSINESS": flag_business(),
        "CAE_VALUATION": flag_valuation(),
        "CAE_INVESTMENT_THESIS": flag_investment_thesis(),
        "note": "Context Assembly owns cae; this programme uses COMPANY_ANALYSIS",
    }
