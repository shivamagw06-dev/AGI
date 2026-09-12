"""SSL feature flags — soft layer only."""

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
    return bool(getattr(s, "simulation_lab", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "simulation_lab", True)) and bool(getattr(s, name, default))


def flags_dict() -> dict[str, Any]:
    return {
        "SIMULATION_LAB": is_enabled(),
        "SSL_SCENARIO": _sub("ssl_scenario"),
        "SSL_PORTFOLIO": _sub("ssl_portfolio"),
        "SSL_MACRO": _sub("ssl_macro"),
        "SSL_STRESS": _sub("ssl_stress"),
        "SSL_STRATEGY": _sub("ssl_strategy"),
        "SSL_DECISION": _sub("ssl_decision"),
        "SSL_SENSITIVITY": _sub("ssl_sensitivity"),
        "SSL_MONTE_CARLO": _sub("ssl_monte_carlo"),
        "SSL_REPLAY": _sub("ssl_replay"),
    }
