"""Historical Coverage Engine — what history exists, per metric, before any reasoning.

Coverage is computed per *metric*, not per dataset. That distinction is load
bearing: inside one valuation table Axis Bank's price reaches back to 1998 while
its P/B only reaches May 2023, because each multiple depends on a different
statement input. A dataset-level answer would claim decades of P/B history that
does not exist.

No reasoning module may bypass this layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from historical_intelligence import periods
from institutional_warehouse import history
from institutional_warehouse.values import normalise_entity, to_date

# Confidence bands. Deliberately coarse: precision here would be false comfort.
STRONG, MODERATE, WEAK, NONE = "strong", "moderate", "weak", "none"

# What a healthy series looks like, by the cadence the source actually publishes.
_DAILY_METRICS = {"price", "adjusted_price", "volume"}
_ANNUAL_METRICS = {
    "revenue", "ebitda", "pat", "eps", "equity", "debt", "cash", "free_cash_flow",
    "roe", "roce", "net_margin", "ebitda_margin", "debt_equity",
}


def _years_between(first: Optional[str], last: Optional[str]) -> Optional[float]:
    # Statement series are labelled FY07, not 2007-03-31, so resolve both forms.
    a, b = periods.comparable(first), periods.comparable(last)
    if not a or not b:
        return None
    delta = datetime.fromisoformat(b) - datetime.fromisoformat(a)
    return round(delta.days / 365.25, 2)


def _period_index(period: str) -> Optional[str]:
    """Fiscal labels sort correctly as text; dates already do."""
    if not period:
        return None
    return to_date(period) or str(period)


def _expected_points(metric: str, years: Optional[float]) -> Optional[int]:
    if years is None or years <= 0:
        return None
    if metric in _DAILY_METRICS:
        return int(years * 250)
    if metric in _ANNUAL_METRICS:
        return max(int(years), 1)
    return max(int(years * 4), 1)  # quarterly-ish cadence for valuation snapshots


def _gaps(labels: list[str], metric: str) -> list[dict[str, Any]]:
    """Holes big enough to change a conclusion, expressed in days."""
    dated = [periods.comparable(p) for p in labels]
    dated = sorted(d for d in dated if d)
    if len(dated) < 2:
        return []
    budget = 45 if metric in _DAILY_METRICS else 500
    out = []
    for earlier, later in zip(dated, dated[1:]):
        days = (datetime.fromisoformat(later) - datetime.fromisoformat(earlier)).days
        if days > budget:
            out.append({"from": earlier, "to": later, "days": days})
    return sorted(out, key=lambda g: g["days"], reverse=True)[:10]


def _confidence(*, points: int, years: Optional[float], density: Optional[float],
                gap_count: int, recency_days: Optional[int]) -> tuple[str, float]:
    if points == 0:
        return NONE, 0.0
    score = 0.0
    # Span carries the most weight: a long history is what makes a historical
    # statement worth making at all.
    if years is not None:
        score += min(years / 10.0, 1.0) * 0.45
    score += min(points / 40.0, 1.0) * 0.2
    if density is not None:
        score += min(density, 1.0) * 0.15
    score += (0.1 if gap_count == 0 else max(0.0, 0.1 - gap_count * 0.02))
    if recency_days is not None:
        score += 0.1 if recency_days <= 45 else (0.05 if recency_days <= 200 else 0.0)
    score = round(min(score, 1.0), 3)
    if score >= 0.7:
        return STRONG, score
    if score >= 0.4:
        return MODERATE, score
    return WEAK, score


def metric_coverage(symbol: str, metric: str) -> dict[str, Any]:
    """Coverage for one company and one metric. The gate every module passes through."""
    ticker = normalise_entity(symbol)
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}
    if metric not in history.SERIES:
        return {"ok": False, "error": f"unknown_metric:{metric}",
                "available": sorted(history.SERIES)}

    series = history.series(ticker, metric, window="max")
    points = series.get("points") or []
    period_labels = [str(p["period"]) for p in points]
    first = period_labels[0] if period_labels else None
    last = period_labels[-1] if period_labels else None
    years = _years_between(first, last)
    expected = _expected_points(metric, years)
    density = round(len(points) / expected, 3) if expected else None

    recency_days = None
    last_date = periods.comparable(last) if last else None
    if last_date:
        recency_days = (datetime.now(timezone.utc).date()
                        - datetime.fromisoformat(last_date).date()).days

    gaps = _gaps(period_labels, metric)
    label, score = _confidence(points=len(points), years=years, density=density,
                               gap_count=len(gaps), recency_days=recency_days)

    return {
        "ok": True,
        "symbol": ticker,
        "metric": metric,
        "tab": history.SERIES[metric]["tab"],
        "earliest": first,
        "latest": last,
        "observations": len(points),
        "years": years,
        "expected_observations": expected,
        "density": density,
        "gaps": gaps,
        "gap_count": len(gaps),
        "recency_days": recency_days,
        "confidence": label,
        "confidence_score": score,
        "window_label": _window_label(first, last),
    }


def _window_label(first: Optional[str], last: Optional[str]) -> str:
    if not first:
        return "no observations"
    latest = "present" if _is_recent(last) else str(last)
    return f"{first} to {latest}"


def _is_recent(period: Optional[str]) -> bool:
    stamp = periods.comparable(period) if period else None
    if not stamp:
        return False
    age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(stamp).date()).days
    return age <= 10


def company_coverage(symbol: str, *, metrics: Optional[Iterable[str]] = None) -> dict[str, Any]:
    """Coverage across the metrics a historical answer is likely to need."""
    ticker = normalise_entity(symbol)
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}
    wanted = list(metrics) if metrics else [
        "price", "revenue", "pat", "eps", "roe", "net_margin", "pe", "pb",
        "ev_ebitda", "dividend_yield", "target_price", "promoter_holding",
    ]
    covered: dict[str, Any] = {}
    for metric in wanted:
        if metric in history.SERIES:
            covered[metric] = metric_coverage(ticker, metric)

    present = [c for c in covered.values() if c.get("observations")]
    deepest = max(present, key=lambda c: c.get("years") or 0.0, default=None)
    return {
        "ok": True,
        "symbol": ticker,
        "metrics": covered,
        "metrics_with_history": [m for m, c in covered.items() if c.get("observations")],
        "metrics_without_history": [m for m, c in covered.items() if not c.get("observations")],
        "deepest_metric": (deepest or {}).get("metric"),
        "deepest_years": (deepest or {}).get("years"),
        "summary": _coverage_sentence(ticker, covered),
    }


def _coverage_sentence(ticker: str, covered: dict[str, Any]) -> str:
    """One line a person can read, because coverage is part of the answer."""
    lines = []
    for metric in ("price", "revenue", "pe", "pb", "target_price"):
        entry = covered.get(metric)
        if entry and entry.get("observations"):
            lines.append(f"{metric} {entry['window_label']}")
    if not lines:
        return f"AGIB holds no historical observations for {ticker}."
    return f"{ticker} observed history — " + "; ".join(lines) + "."


def dataset_coverage(symbol: str) -> dict[str, Any]:
    """Per-tab view, for the dashboard. Modules use metric_coverage instead."""
    ticker = normalise_entity(symbol)
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}
    return {"ok": True, "symbol": ticker, **history.coverage(ticker)}
