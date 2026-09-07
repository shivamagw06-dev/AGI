"""PIO feature flags — soft layer only."""

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
    return bool(getattr(s, "portfolio_intelligence", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "portfolio_intelligence", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "PORTFOLIO_INTELLIGENCE": is_enabled(),
        "PIO_ALLOCATION": _sub("pio_allocation"),
        "PIO_RISK": _sub("pio_risk"),
        "PIO_DIVERSIFICATION": _sub("pio_diversification"),
        "PIO_FACTORS": _sub("pio_factors"),
        "PIO_SCENARIOS": _sub("pio_scenarios"),
        "PIO_OPTIMISATION": _sub("pio_optimisation"),
        "PIO_POSITION_SIZING": _sub("pio_position_sizing"),
        "PIO_OVERLAP": _sub("pio_overlap"),
        "PIO_QUALITY": _sub("pio_quality"),
    }
