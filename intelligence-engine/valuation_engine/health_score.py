"""Valuation Health Score — confidence in the analysis, not the company.

This is deliberately not an investment score. A large-cap with live prices,
complete financials and consensus can score 94%; a small name with one year of
history and no ROE can score 62% even if its business is fine. The analyst
learns how much weight to put on the valuation view itself.
"""

from __future__ import annotations

from typing import Any, Optional


def score(
    *,
    metrics: dict[str, Any],
    coverage: dict[str, Any],
    provenance: dict[str, Any],
    history_span_years: Optional[float],
    history_observations: int,
    conflict_count: int,
    override_count: int,
    quality_flags: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build a 0–100 confidence score with explicit reasons."""
    reasons_ok: list[str] = []
    reasons_missing: list[str] = []
    points = 0.0
    possible = 0.0

    def check(label_ok: str, label_miss: str, weight: float, ok: bool) -> None:
        nonlocal points, possible
        possible += weight
        if ok:
            points += weight
            reasons_ok.append(label_ok)
        else:
            reasons_missing.append(label_miss)

    price = provenance.get("price") or {}
    financials = provenance.get("financials") or {}
    consensus = provenance.get("consensus") or {}

    check("Live price", "No live price", 18.0, bool(price.get("source") or metrics.get("cmp", {}).get("available")))
    check(
        "Latest financials",
        "Financials unavailable",
        18.0,
        bool(financials.get("source") or metrics.get("eps", {}).get("available")),
    )
    check(
        "Complete historical coverage",
        "Historical coverage incomplete",
        16.0,
        bool(history_span_years and history_span_years >= 5 and history_observations >= 20),
    )
    if history_span_years and history_span_years < 5:
        if history_span_years < 1:
            reasons_missing[-1] = "Only under 1 year valuation history"
        else:
            reasons_missing[-1] = f"Only {history_span_years:.0f} year valuation history"

    check("Consensus available", "Consensus unavailable", 12.0, bool(consensus.get("source") or metrics.get("target_price", {}).get("available")))
    check("ROE available", "No ROE", 10.0, bool((metrics.get("roe") or {}).get("available")))
    check("No data conflicts", f"{conflict_count} data conflict(s)", 12.0, conflict_count == 0)
    check("No overrides", f"{override_count} override(s)", 6.0, override_count == 0)

    coverage_pct = float(coverage.get("pct") or 0.0)
    check("Metric coverage ≥ 70%", f"Metric coverage {coverage_pct:.0f}%", 8.0, coverage_pct >= 70.0)

    dqiv = (quality_flags or {}).get("dqiv_passed")
    if dqiv is True:
        reasons_ok.append("DQIV Passed")
    elif dqiv is False:
        reasons_missing.append("DQIV failed")

    pct = round(100.0 * points / possible, 0) if possible else 0.0
    band = "high" if pct >= 85 else "moderate" if pct >= 60 else "low"

    return {
        "score": int(pct),
        "band": band,
        "label": "Valuation Confidence",
        "reasons_ok": reasons_ok,
        "reasons_missing": reasons_missing,
        "components": {
            "points": round(points, 1),
            "possible": round(possible, 1),
            "history_span_years": history_span_years,
            "history_observations": history_observations,
            "conflicts": conflict_count,
            "overrides": override_count,
            "coverage_pct": coverage_pct,
        },
    }
