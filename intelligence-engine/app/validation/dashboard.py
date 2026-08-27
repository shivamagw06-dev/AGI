"""BT-005 Validation Dashboard payload builder."""

from __future__ import annotations

from typing import Any

from app.validation.models import ReplayDaySlice, ValidationSummary


def build_dashboard(days: list[ReplayDaySlice], summary: ValidationSummary | None) -> dict[str, Any]:
    """Assemble dashboard sections: timeline, portfolio, signals, L4 vs E03, distributions."""
    timeline = [
        {
            "as_of": d.as_of,
            "portfolio_return": d.portfolio_return,
            "benchmark_return": d.benchmark_return,
            "cash": d.cash_allocation,
            "e01_regime": d.e01_regime,
            "e14_risk_level": d.e14_risk_level,
            "n_positions": len(d.portfolio_weights),
        }
        for d in days
    ]
    portfolio_history = [
        {
            "as_of": d.as_of,
            "weights": d.portfolio_weights,
            "cash_allocation": d.cash_allocation,
            "expected_volatility": d.expected_volatility,
            "portfolio_hash": d.portfolio_hash,
        }
        for d in days
    ]
    signal_history = [
        {
            "as_of": d.as_of,
            "e03_scores": d.e03_scores,
            "e03_labels": d.e03_labels,
            "l4_scores": d.l4_scores,
            "l4_labels": d.l4_labels,
            "confidences": d.confidences,
        }
        for d in days
    ]
    l4_vs_e03 = []
    for d in days:
        syms = set(d.e03_labels) | set(d.l4_labels)
        agree = 0
        n = 0
        rows = []
        for s in sorted(syms):
            e3 = d.e03_labels.get(s)
            l4 = d.l4_labels.get(s)
            match = e3 == l4
            if e3 is not None and l4 is not None:
                n += 1
                if match:
                    agree += 1
            rows.append(
                {
                    "symbol": s,
                    "e03_label": e3,
                    "l4_label": l4,
                    "e03_score": d.e03_scores.get(s),
                    "l4_score": d.l4_scores.get(s),
                    "agreement": match,
                }
            )
        l4_vs_e03.append(
            {
                "as_of": d.as_of,
                "agreement_rate": round(agree / n, 6) if n else None,
                "rows": rows,
            }
        )

    conf_vals = [c for d in days for c in d.confidences.values()]
    risk_levels = [d.e14_risk_level for d in days if d.e14_risk_level]
    conf_dist = _histogram(conf_vals, edges=[0.0, 0.5, 0.6, 0.7, 0.8, 1.01])
    risk_dist: dict[str, int] = {}
    for r in risk_levels:
        risk_dist[r] = risk_dist.get(r, 0) + 1

    return {
        "timeline": timeline,
        "portfolio_history": portfolio_history,
        "signal_history": signal_history,
        "l4_vs_e03": l4_vs_e03,
        "confidence_distribution": conf_dist,
        "risk_distribution": risk_dist,
        "summary": summary.model_dump(mode="json") if summary else None,
    }


def _histogram(values: list[float], edges: list[float]) -> list[dict[str, Any]]:
    if not values:
        return []
    bins: list[dict[str, Any]] = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        count = sum(1 for v in values if lo <= v < hi)
        bins.append({"lo": lo, "hi": hi, "count": count})
    return bins
