"""Shared metric helpers for pillar scoring (deterministic)."""

from __future__ import annotations

from typing import Any

from evidence_fusion.signals import build_signal_map, metric_signal
from financial_intelligence.trends import normalize_series


def series_volatility(series: list[dict[str, Any]] | None) -> float | None:
    """Coefficient of variation of period-over-period % changes (lower = more consistent)."""
    rows = normalize_series(series or [])
    if len(rows) < 3:
        return None
    pcts: list[float] = []
    for i in range(1, len(rows)):
        prev, curr = float(rows[i - 1]["value"]), float(rows[i]["value"])
        if prev == 0:
            continue
        pcts.append(100.0 * (curr - prev) / abs(prev))
    if len(pcts) < 2:
        return None
    mean = sum(pcts) / len(pcts)
    var = sum((p - mean) ** 2 for p in pcts) / len(pcts)
    std = var**0.5
    if abs(mean) < 1e-9:
        return std
    return abs(std / mean)


def multi_year_direction(series: list[dict[str, Any]] | None) -> str | None:
    rows = normalize_series(series or [])
    if len(rows) < 2:
        return None
    first, last = float(rows[0]["value"]), float(rows[-1]["value"])
    if abs(first) < 1e-12:
        return "up" if last > first else ("down" if last < first else "flat")
    pct = 100.0 * (last - first) / abs(first)
    if abs(pct) < 1.0:
        return "flat"
    return "up" if pct > 0 else "down"


def clamp_score(points: float, *, lo: float = 0.0, hi: float = 100.0) -> float:
    return round(max(lo, min(hi, points)), 2)


def make_finding(
    *,
    pillar_id: str,
    title: str,
    score: float | None,
    evidence: list[dict[str, Any]],
    confidence: str,
    supporting_modules: list[str],
    narrative: str,
    components: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "pillar": title,
        "pillar_id": pillar_id,
        "score": score,
        "evidence": evidence,
        "confidence": confidence,
        "supporting_modules": supporting_modules,
        "narrative": narrative,
        "components": components or {},
        "uses_llm": False,
        "recommendation": None,
    }


def signals_for(series_map: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    return build_signal_map(series_map)


def direction_points(direction: str | None, *, favorable: str = "up") -> float:
    if direction is None or direction == "unknown":
        return 0.0
    if direction == favorable:
        return 12.0
    if direction == "flat":
        return 6.0
    return -8.0


__all__ = [
    "clamp_score",
    "direction_points",
    "make_finding",
    "metric_signal",
    "multi_year_direction",
    "series_volatility",
    "signals_for",
]
