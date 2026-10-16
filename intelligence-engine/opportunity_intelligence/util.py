"""Shared helpers — deterministic, no opaque scoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from opportunity_intelligence.schema import TICKER_ALIASES


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_ticker(ticker: str) -> str:
    key = (ticker or "").upper().replace(".NS", "").replace(".BO", "").strip()
    return TICKER_ALIASES.get(key, key)


def display_ticker(ticker: str) -> str:
    key = resolve_ticker(ticker)
    if key == "TMPV":
        return "TATAMOTORS"
    return key


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(v)))


def round1(v: float | None) -> float | None:
    if v is None:
        return None
    return round(float(v), 1)


def as_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def deep_get(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def dim_result(
    *,
    score: float,
    signals: list[str],
    evidence: list[dict[str, Any]],
    available: bool,
    coverage: float,
) -> dict[str, Any]:
    return {
        "score": round1(clamp(score)),
        "signals": signals[:12],
        "evidence": evidence[:16],
        "available": available,
        "coverage": round1(clamp(coverage)),
    }
