"""PIL feature flags — soft layer only."""

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
    return bool(getattr(s, "peer_intelligence", True))


def _sub(name: str, default: bool = True) -> bool:
    s = _settings()
    if s is None:
        return default
    return bool(getattr(s, "peer_intelligence", True)) and bool(getattr(s, name, default))


def flag_peers() -> bool:
    return _sub("pil_peers")


def flag_history() -> bool:
    return _sub("pil_history")


def flag_percentiles() -> bool:
    return _sub("pil_percentiles")


def flag_rankings() -> bool:
    return _sub("pil_rankings")


def flag_benchmarks() -> bool:
    return _sub("pil_benchmarks")


def flag_commentary() -> bool:
    return _sub("pil_commentary")


def flag_scorecards() -> bool:
    return _sub("pil_scorecards")


def flags_dict() -> dict[str, Any]:
    return {
        "PEER_INTELLIGENCE": is_enabled(),
        "PIL_PEERS": flag_peers(),
        "PIL_HISTORY": flag_history(),
        "PIL_PERCENTILES": flag_percentiles(),
        "PIL_RANKINGS": flag_rankings(),
        "PIL_BENCHMARKS": flag_benchmarks(),
        "PIL_COMMENTARY": flag_commentary(),
        "PIL_SCORECARDS": flag_scorecards(),
    }
