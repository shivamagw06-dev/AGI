"""Deterministic trend engine — QoQ / YoY / 3y / 5y when available."""

from __future__ import annotations

from datetime import date
from typing import Any

from financial_intelligence.schema import MARGIN_METRICS, WINDOWS


def _parse_period(value: Any) -> date | None:
    if value is None:
        return None
    s = str(value).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def normalize_series(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort ascending by period; keep latest value per period."""
    by_pe: dict[str, dict[str, Any]] = {}
    for p in points or []:
        pe = str(p.get("period") or p.get("reporting_period") or "").strip()[:10]
        if not pe:
            continue
        val = p.get("value")
        if not isinstance(val, (int, float)):
            continue
        prev = by_pe.get(pe)
        ver = int(p.get("version") or 0)
        if prev is None or ver >= int(prev.get("version") or 0):
            by_pe[pe] = {
                "period": pe,
                "value": float(val),
                "version": ver,
                "warehouse_version": p.get("warehouse_version"),
                "validation_id": p.get("validation_id"),
                "validation_status": p.get("validation_status"),
                "quality_score": p.get("quality_score"),
                "fact_key": p.get("fact_key"),
                "metric": p.get("metric") or p.get("canonical_metric"),
            }
    return sorted(by_pe.values(), key=lambda r: r["period"])


def _pct_change(curr: float, prior: float) -> float | None:
    if prior == 0:
        return None
    return round(100.0 * (curr - prior) / abs(prior), 4)


def _bps_change(curr: float, prior: float) -> float:
    """Margin-style: treat values as percentages (18.0 vs 15.8 → +220 bps)."""
    return round((curr - prior) * 100.0, 2)


def _direction(delta: float | None, *, invert_good: bool = False) -> str:
    if delta is None:
        return "unknown"
    if abs(delta) < 1e-9:
        return "flat"
    up = delta > 0
    if invert_good:
        return "improving" if not up else "deteriorating"
    return "up" if up else "down"


def _find_prior(series: list[dict[str, Any]], latest_pe: date, *, months: int) -> dict[str, Any] | None:
    """Find point closest to latest_pe - months (tolerance ±45 days for quarter alignment)."""
    target_year = latest_pe.year
    target_month = latest_pe.month - months
    while target_month <= 0:
        target_month += 12
        target_year -= 1
    # Prefer exact year-ago / n-year-ago same month-day if present
    target = date(target_year, latest_pe.month, min(latest_pe.day, 28))
    # For YoY with annual Mar 31 → prior Mar 31
    if months % 12 == 0:
        years = months // 12
        exact = date(latest_pe.year - years, latest_pe.month, latest_pe.day)
        for p in series:
            pe = _parse_period(p["period"])
            if pe == exact:
                return p
    # QoQ: prefer ~90 days earlier
    best = None
    best_diff = None
    for p in series:
        pe = _parse_period(p["period"])
        if pe is None or pe >= latest_pe:
            continue
        diff = abs((latest_pe - pe).days - int(months * 30.4))
        if best_diff is None or diff < best_diff:
            best_diff = diff
            best = p
    if best is None or best_diff is None:
        return None
    # QoQ tolerance 60d; multi-year looser
    tol = 60 if months <= 3 else 120
    if best_diff > tol:
        return None
    return best


def compare_window(
    series: list[dict[str, Any]],
    *,
    window: str,
    metric: str,
) -> dict[str, Any] | None:
    """Return one window comparison or None if insufficient history."""
    if window not in WINDOWS:
        return None
    s = normalize_series(series)
    if len(s) < 2:
        return None
    latest = s[-1]
    pe = _parse_period(latest["period"])
    if pe is None:
        return None
    months = {"qoq": 3, "yoy": 12, "y3": 36, "y5": 60}[window]
    prior = _find_prior(s, pe, months=months)
    if prior is None:
        return None
    curr_v = float(latest["value"])
    prior_v = float(prior["value"])
    is_margin = metric in MARGIN_METRICS
    if is_margin:
        delta = _bps_change(curr_v, prior_v)
        unit = "bps"
        pct = None
    else:
        pct = _pct_change(curr_v, prior_v)
        delta = pct
        unit = "pct"
    invert = metric in {"total_debt"}  # rising debt often negative; direction still "up/down"
    return {
        "window": window,
        "metric": metric,
        "current_period": latest["period"],
        "prior_period": prior["period"],
        "current_value": curr_v,
        "prior_value": prior_v,
        "change": delta,
        "change_unit": unit,
        "pct_change": pct,
        "direction": _direction(delta if not is_margin else (curr_v - prior_v), invert_good=False),
        "warehouse_version": latest.get("warehouse_version") or prior.get("warehouse_version"),
        "validation_id": latest.get("validation_id"),
        "evidence": {
            "metric": metric,
            "current": {"period": latest["period"], "value": curr_v, "version": latest.get("version")},
            "prior": {"period": prior["period"], "value": prior_v, "version": prior.get("version")},
            "warehouse_version": latest.get("warehouse_version"),
            "validation_id": latest.get("validation_id"),
            "validation_status": latest.get("validation_status"),
        },
    }


def detect_trends(metric: str, series: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect all available windows for one metric."""
    windows: dict[str, Any] = {}
    for w in WINDOWS:
        cmp_ = compare_window(series, window=w, metric=metric)
        if cmp_:
            windows[w] = cmp_
    label = None
    yoy = windows.get("yoy")
    qoq = windows.get("qoq")
    primary = yoy or qoq or next(iter(windows.values()), None)
    if primary:
        ch = primary.get("change")
        unit = primary.get("change_unit")
        direction = primary.get("direction")
        if metric == "revenue":
            if direction == "up":
                qoq_pct = qoq.get("pct_change") if qoq else None
                yoy_pct = yoy.get("pct_change") if yoy else None
                if qoq_pct is not None and yoy_pct is not None and qoq_pct < yoy_pct:
                    label = "revenue_deceleration"
                elif (ch or 0) >= 10:
                    label = "revenue_acceleration"
                else:
                    label = "revenue_growth"
            elif direction == "down":
                label = "revenue_deceleration"
            else:
                label = "revenue_flat"
        elif metric in MARGIN_METRICS:
            label = "margin_expansion" if direction == "up" else ("margin_compression" if direction == "down" else "margin_flat")
        elif metric in {"roe", "roce"}:
            label = f"{metric}_improving" if direction == "up" else (f"{metric}_declining" if direction == "down" else f"{metric}_flat")
        elif metric == "total_debt":
            label = "debt_rising" if direction == "up" else ("debt_falling" if direction == "down" else "debt_flat")
        elif metric == "cash":
            label = "cash_rising" if direction == "up" else ("cash_falling" if direction == "down" else "cash_flat")
        elif metric == "working_capital":
            label = "working_capital_rising" if direction == "up" else ("working_capital_falling" if direction == "down" else "working_capital_flat")
        elif metric in {"free_cash_flow", "operating_cash_flow"}:
            label = "fcf_improving" if direction == "up" else ("fcf_declining" if direction == "down" else "fcf_flat")
        elif metric in {"eps_basic", "net_income"}:
            label = "eps_growth" if direction == "up" else ("eps_decline" if direction == "down" else "eps_flat")
        else:
            label = f"{metric}_{direction}"
        _ = unit  # reserved for narrative
    return {
        "metric": metric,
        "n_points": len(normalize_series(series)),
        "windows": windows,
        "trend_label": label,
        "primary_window": (primary or {}).get("window"),
        "primary": primary,
    }
