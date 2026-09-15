"""CIG feature flags — soft layer only."""

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
    return bool(getattr(s, "causal_intelligence", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "causal_intelligence", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "CAUSAL_INTELLIGENCE": is_enabled(),
        "CIG_TRANSMISSION": _sub("cig_transmission"),
        "CIG_PROPAGATION": _sub("cig_propagation"),
        "CIG_COUNTERFACTUAL": _sub("cig_counterfactual"),
        "CIG_SECTOR_MODELS": _sub("cig_sector_models"),
        "CIG_PORTFOLIO_IMPACT": _sub("cig_portfolio_impact"),
        "CIG_HISTORICAL": _sub("cig_historical"),
        "CIG_CONFIDENCE": _sub("cig_confidence"),
    }
