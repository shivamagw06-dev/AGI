"""Valuation conditioning, peer ranking and independent-source reconciliation."""

from __future__ import annotations

import statistics
from typing import Any


def percentile_rank(current: float | None, values: list[float | None]) -> float | None:
    clean = sorted(float(v) for v in values if isinstance(v, (int, float)) and float(v) > 0)
    if current is None or not clean:
        return None
    return round(100.0 * sum(v <= float(current) for v in clean) / len(clean), 1)


def premium_discount(current: float | None, reference: float | None) -> float | None:
    if current is None or reference in (None, 0):
        return None
    return round((float(current) / float(reference) - 1.0) * 100.0, 1)


def quality_matrix(
    *, historical_percentile: float | None, peer_premium_pct: float | None,
    roe: float | None, peer_roe: float | None, eps_cagr: float | None,
    peer_eps_cagr: float | None, leverage: float | None = None,
    peer_leverage: float | None = None,
) -> dict[str, Any]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    neutral: list[str] = []
    if roe is not None and peer_roe is not None:
        (strengths if roe >= peer_roe * 1.05 else weaknesses if roe <= peer_roe * 0.95 else neutral).append(
            "ROE above peers" if roe >= peer_roe * 1.05 else "ROE below peers" if roe <= peer_roe * 0.95 else "ROE in line"
        )
    if eps_cagr is not None and peer_eps_cagr is not None:
        (strengths if eps_cagr >= peer_eps_cagr + 1 else weaknesses if eps_cagr <= peer_eps_cagr - 1 else neutral).append(
            "growth above peers" if eps_cagr >= peer_eps_cagr + 1 else "growth below peers" if eps_cagr <= peer_eps_cagr - 1 else "growth in line"
        )
    if leverage is not None and peer_leverage is not None:
        (strengths if leverage <= peer_leverage * 0.9 else weaknesses if leverage >= peer_leverage * 1.1 else neutral).append(
            "leverage below peers" if leverage <= peer_leverage * 0.9 else "leverage above peers" if leverage >= peer_leverage * 1.1 else "leverage in line"
        )
    high_valuation = bool(
        (historical_percentile is not None and historical_percentile >= 70)
        or (peer_premium_pct is not None and peer_premium_pct >= 10)
    )
    strong = len(strengths) > len(weaknesses)
    label = (
        "QUALITY_PREMIUM" if high_valuation and strong else
        "OVERVALUATION_RISK" if high_valuation else
        "POTENTIALLY_ATTRACTIVE" if strong else
        "VALUE_TRAP_RISK"
    )
    return {
        "label": label, "valuation": "HIGH" if high_valuation else "LOW_OR_FAIR",
        "fundamentals": "STRONG" if strong else "WEAK_OR_UNCONFIRMED",
        "supporting_fundamentals": strengths, "offsetting_fundamentals": weaknesses,
        "neutral_fundamentals": neutral,
    }


def reconcile_sources(values: dict[str, Any], *, tolerance_pct: float = 10.0) -> dict[str, Any]:
    clean = {k: float(v) for k, v in values.items() if isinstance(v, (int, float)) and float(v) > 0}
    if len(clean) < 2:
        return {"status": "INSUFFICIENT_SOURCES", "values": clean, "tolerance_pct": tolerance_pct}
    median = statistics.median(clean.values())
    deviations = {k: round(abs(v / median - 1.0) * 100.0, 2) for k, v in clean.items()}
    conflict = any(value > tolerance_pct for value in deviations.values())
    return {
        "status": "VALUATION_DATA_CONFLICT" if conflict else "ACCEPTED",
        "values": clean, "median": round(median, 4), "deviation_pct": deviations,
        "tolerance_pct": tolerance_pct,
        "investigation": ["denominator", "as_of_date", "consolidated_vs_standalone", "market_price_timestamp"] if conflict else [],
    }
