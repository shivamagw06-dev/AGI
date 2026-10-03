"""Historical Valuation Intelligence Engine — read path.

Reads append-only warehouse observations (reconstructed from prices +
statements), applies VPAE applicability, and produces statistics, bands,
percentiles, regimes, and re-/de-rating intelligence.
"""

from __future__ import annotations

from typing import Any, Optional

from historical_valuation_intelligence import dqiv
from historical_valuation_intelligence.models import (
    ENGINE_CODE,
    METRICS,
    SERIES_ALIASES,
    VERSION,
    WINDOWS,
)
from historical_valuation_intelligence.statistics import (
    all_window_stats,
    bands_from_stats,
    compute_stats,
    filter_points,
    regime_from_percentile,
)


def _policy(symbol: str) -> dict[str, Any]:
    try:
        from valuation_policy import evaluate

        return evaluate(symbol) or {}
    except Exception:
        return {}


def _metric_applicable(metric: str, policy: dict[str, Any]) -> dict[str, Any]:
    if not policy or not policy.get("ok"):
        return {"applicable": True, "status": "Applicable", "reason": "No policy — default allow."}
    try:
        from valuation_policy import is_meaningful

        ok = is_meaningful(metric, policy)
    except Exception:
        ok = metric not in (policy.get("hidden_metrics") or [])
    if not ok:
        entry = (policy.get("metrics") or {}).get(metric) or {}
        return {
            "applicable": False,
            "status": entry.get("status") or "Hidden",
            "reason": entry.get("reason")
            or f"{metric.upper()} suppressed by valuation policy "
            f"({policy.get('status')}).",
            "primary_model": policy.get("primary_model"),
        }
    return {
        "applicable": True,
        "status": "Applicable",
        "reason": f"Permitted under primary model {policy.get('primary_model')}.",
        "primary_model": policy.get("primary_model"),
    }


def _load_points(symbol: str, metric: str) -> list[dict[str, Any]]:
    from institutional_warehouse import history

    series_key = SERIES_ALIASES.get(metric, metric)
    series = history.series(symbol, series_key, window="max", limit=20000)
    if not series.get("ok"):
        return []
    return [
        {"period": p.get("period"), "date": p.get("period"), "value": p.get("value"),
         "source": p.get("source")}
        for p in (series.get("points") or [])
        if p.get("value") is not None
    ]


def _confidence(stats: dict[str, Any], series_dqiv: dict[str, Any]) -> str:
    n = int(stats.get("observation_count") or 0)
    span = stats.get("span_years") or 0
    if not stats.get("ok") or n < 6:
        return "LOW"
    if series_dqiv.get("status") == "fail":
        return "LOW"
    if n >= 60 and span and span >= 5 and series_dqiv.get("status") in {"ok", "warn"}:
        return "HIGH"
    if n >= 24:
        return "MEDIUM"
    return "LOW"


def _unavailable(metric: str, policy_gate: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "metric": metric,
        "status": "NOT_APPLICABLE" if not policy_gate.get("applicable") else "UNAVAILABLE",
        "reason": policy_gate.get("reason") if not policy_gate.get("applicable") else reason,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def history_for(
    symbol: str,
    *,
    metric: Optional[str] = None,
    window: str = "max",
    limit: int = 5000,
) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    policy = _policy(ticker)
    metrics = [metric] if metric else list(METRICS)
    series_out: dict[str, Any] = {}
    for m in metrics:
        gate = _metric_applicable(m, policy)
        if not gate["applicable"]:
            series_out[m] = {
                "ok": False,
                "metric": m,
                "status": "NOT_APPLICABLE",
                "reason": gate["reason"],
                "points": [],
                "count": 0,
            }
            continue
        points = filter_points(_load_points(ticker, m), window=window)[-limit:]
        series_dq = dqiv.validate_series(points, m)
        series_out[m] = {
            "ok": True,
            "metric": m,
            "window": window,
            "points": points,
            "count": len(points),
            "first": points[0]["period"] if points else None,
            "last": points[-1]["period"] if points else None,
            "dqiv": series_dq,
            "applicability": gate,
            "source": "warehouse.historical_valuation (reconstructed)",
        }
    return {
        "ok": True,
        "symbol": ticker,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "window": window,
        "policy": {
            "primary_model": policy.get("primary_model"),
            "status": policy.get("status"),
            "confidence": policy.get("confidence"),
        } if policy.get("ok") else None,
        "series": series_out,
        "vendor_historical_ratios": False,
    }


def statistics_for(
    symbol: str,
    *,
    metric: str = "pe",
    window: Optional[str] = None,
) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    policy = _policy(ticker)
    gate = _metric_applicable(metric, policy)
    if not gate["applicable"]:
        return {**_unavailable(metric, gate, gate["reason"]), "symbol": ticker}

    points = _load_points(ticker, metric)
    if not points:
        return {
            "ok": False,
            "symbol": ticker,
            "metric": metric,
            "status": "UNAVAILABLE",
            "reason": "No reconstructed historical observations in warehouse.",
            "engine": ENGINE_CODE,
            "version": VERSION,
        }

    if window:
        filtered = filter_points(points, window=window)
        stats = compute_stats(filtered)
        series_dq = dqiv.validate_series(filtered, metric)
        return {
            "ok": bool(stats.get("ok")),
            "symbol": ticker,
            "metric": metric,
            "window": window,
            "stats": stats,
            "regime": regime_from_percentile(stats.get("current_percentile")),
            "confidence": _confidence(stats, series_dq),
            "dqiv": series_dq,
            "applicability": gate,
            "engine": ENGINE_CODE,
            "version": VERSION,
        }

    by_window = all_window_stats(points)
    primary = by_window.get("max") or {}
    series_dq = dqiv.validate_series(points, metric)
    return {
        "ok": True,
        "symbol": ticker,
        "metric": metric,
        "windows": by_window,
        "available_windows": [w for w, s in by_window.items() if s.get("ok")],
        "regime": regime_from_percentile(primary.get("current_percentile")),
        "confidence": _confidence(primary, series_dq),
        "dqiv": series_dq,
        "applicability": gate,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def bands_for(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    pack = statistics_for(symbol, metric=metric, window=window)
    if not pack.get("ok"):
        return pack
    stats = pack.get("stats") or {}
    bands = bands_from_stats(stats)
    return {
        **bands,
        "symbol": str(symbol).upper(),
        "metric": metric,
        "window": window,
        "current_percentile": stats.get("current_percentile"),
        "premium_to_median_pct": stats.get("premium_to_median_pct"),
        "regime": pack.get("regime"),
        "confidence": pack.get("confidence"),
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def percentiles_for(symbol: str, *, metric: str = "pe") -> dict[str, Any]:
    pack = statistics_for(symbol, metric=metric)
    if not pack.get("ok"):
        return pack
    windows = pack.get("windows") or {}
    out = {}
    for w, stats in windows.items():
        if not stats.get("ok"):
            continue
        out[w] = {
            "current": stats.get("current"),
            "current_percentile": stats.get("current_percentile"),
            "median": stats.get("median"),
            "premium_to_median_pct": stats.get("premium_to_median_pct"),
            "observation_count": stats.get("observation_count"),
            "span_years": stats.get("span_years"),
            "interpretation": _percentile_prose(
                stats.get("current_percentile"), metric=metric
            ),
        }
    return {
        "ok": True,
        "symbol": str(symbol).upper(),
        "metric": metric,
        "percentiles": out,
        "regime": pack.get("regime"),
        "confidence": pack.get("confidence"),
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def _percentile_prose(percentile: Optional[float], *, metric: str) -> str:
    if percentile is None:
        return "Historical percentile unavailable."
    label = metric.upper().replace("_", "/")
    return (
        f"The stock traded cheaper than today's {label} during approximately "
        f"{percentile:.0f}% of observed history."
    )


def regimes_for(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    pack = statistics_for(symbol, metric=metric, window=window)
    if not pack.get("ok"):
        return pack
    stats = pack.get("stats") or {}
    regime = pack.get("regime") or regime_from_percentile(stats.get("current_percentile"))
    return {
        "ok": True,
        "symbol": str(symbol).upper(),
        "metric": metric,
        "window": window,
        "regime": regime.get("regime"),
        "percentile": regime.get("percentile"),
        "current": stats.get("current"),
        "median": stats.get("median"),
        "bands": {
            "very_cheap": "0–20%",
            "cheap": "20–40%",
            "fair": "40–60%",
            "expensive": "60–80%",
            "very_expensive": "80–100%",
        },
        "confidence": pack.get("confidence"),
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def rerating_for(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    policy = _policy(ticker)
    gate = _metric_applicable(metric, policy)
    if not gate["applicable"]:
        return {**_unavailable(metric, gate, gate["reason"]), "symbol": ticker}

    points = filter_points(_load_points(ticker, metric), window=window)
    if len(points) < 8:
        return {
            "ok": False,
            "symbol": ticker,
            "metric": metric,
            "error": "insufficient_history_for_rerating",
            "observation_count": len(points),
            "engine": ENGINE_CODE,
            "version": VERSION,
        }

    import statistics as stats_mod

    half = len(points) // 2
    early = stats_mod.median([p["value"] for p in points[:half]])
    late = stats_mod.median([p["value"] for p in points[half:]])
    if not early:
        return {"ok": False, "symbol": ticker, "error": "zero_early_median",
                "engine": ENGINE_CODE, "version": VERSION}
    change = round(100.0 * (late - early) / abs(early), 2)

    # Local extrema for "when cheapest / most expensive"
    lo = min(points, key=lambda p: p["value"])
    hi = max(points, key=lambda p: p["value"])
    current = points[-1]

    if abs(change) < 10:
        direction = "STABLE"
        kind = "stable"
    elif change > 0:
        direction = "RERATING"
        kind = "expansion"
    else:
        direction = "DERATING"
        kind = "compression"

    # Day-over-day style change using last two observations
    daily = None
    if len(points) >= 2:
        prev, curr = points[-2], points[-1]
        if prev["value"]:
            daily_chg = round(100.0 * (curr["value"] - prev["value"]) / abs(prev["value"]), 2)
            daily = {
                "previous": prev["value"],
                "current": curr["value"],
                "previous_date": prev["period"],
                "current_date": curr["period"],
                "change_pct": daily_chg,
                "reason": (
                    f"Multiple moved {daily_chg:+.1f}% between {prev['period']} and "
                    f"{curr['period']} on reconstructed observations (price and/or "
                    f"earnings inputs)."
                ),
            }

    return {
        "ok": True,
        "symbol": ticker,
        "metric": metric,
        "window": window,
        "direction": direction,
        "kind": kind,
        "change_pct": change,
        "early_median": round(early, 4),
        "late_median": round(late, 4),
        "early_window": {"first": points[0]["period"], "last": points[half - 1]["period"]},
        "late_window": {"first": points[half]["period"], "last": points[-1]["period"]},
        "cheapest": {"value": lo["value"], "date": lo["period"]},
        "richest": {"value": hi["value"], "date": hi["period"]},
        "current": {"value": current["value"], "date": current["period"]},
        "daily_change": daily,
        "sentence": (
            f"{'Multiple expansion' if kind == 'expansion' else 'Multiple compression' if kind == 'compression' else 'Multiple stable'}: "
            f"median {metric.upper()} moved {change:+.1f}% from {early:.2f} "
            f"(earlier half) to {late:.2f} (later half) over {window}."
        ),
        "applicability": gate,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def coverage_for(symbol: str, *, metric: Optional[str] = None) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    policy = _policy(ticker)
    metrics = [metric] if metric else list(METRICS)
    out: dict[str, Any] = {}
    for m in metrics:
        gate = _metric_applicable(m, policy)
        points = _load_points(ticker, m) if gate["applicable"] else []
        stats = compute_stats(points) if points else {"ok": False, "observation_count": 0}
        out[m] = {
            "applicable": gate["applicable"],
            "status": gate["status"],
            "reason": None if gate["applicable"] else gate["reason"],
            "observation_count": stats.get("observation_count") or 0,
            "first": stats.get("first"),
            "last": stats.get("last"),
            "span_years": stats.get("span_years"),
            "coverage_label": (
                f"{stats.get('first')} → {stats.get('last')} · "
                f"{stats.get('span_years')} years · "
                f"{stats.get('observation_count')} observations"
                if stats.get("ok")
                else "No observations"
            ),
            "confidence": _confidence(stats, {"status": "ok"}) if stats.get("ok") else "LOW",
        }
    return {
        "ok": True,
        "symbol": ticker,
        "metrics": out,
        "policy": {
            "primary_model": policy.get("primary_model"),
            "status": policy.get("status"),
        } if policy.get("ok") else None,
        "vendor_historical_ratios": False,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def company_pack(
    symbol: str,
    *,
    metric: Optional[str] = None,
    window: str = "10y",
) -> dict[str, Any]:
    """One-response pack for Valuation Terminal / Ask / Research."""
    ticker = str(symbol or "").strip().upper()
    policy = _policy(ticker)
    primary_metric = metric or (policy.get("primary_metric") if policy.get("ok") else None) or "pe"

    stats = statistics_for(ticker, metric=primary_metric, window=window)
    bands = bands_for(ticker, metric=primary_metric, window=window) if stats.get("ok") else {}
    regimes = regimes_for(ticker, metric=primary_metric, window=window) if stats.get("ok") else {}
    rerating = rerating_for(ticker, metric=primary_metric, window=window)
    cover = coverage_for(ticker, metric=primary_metric)
    # Also attach max-window percentile for institutional "vs own history"
    max_stats = statistics_for(ticker, metric=primary_metric, window="max")

    st = stats.get("stats") or {}
    return {
        "ok": True,
        "symbol": ticker,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "metric": primary_metric,
        "window": window,
        "policy": {
            "primary_model": policy.get("primary_model"),
            "primary_metric": policy.get("primary_metric"),
            "status": policy.get("status"),
            "confidence": policy.get("confidence"),
            "reason": policy.get("reason"),
        } if policy.get("ok") else None,
        "current": st.get("current"),
        "median": st.get("median"),
        "historical_percentile": st.get("current_percentile"),
        "premium_to_median_pct": st.get("premium_to_median_pct"),
        "bands": bands if bands.get("ok") else None,
        "regime": regimes.get("regime") if regimes.get("ok") else None,
        "rerating": rerating if rerating.get("ok") else None,
        "coverage": (cover.get("metrics") or {}).get(primary_metric),
        "max_window": {
            "median": (max_stats.get("stats") or {}).get("median"),
            "percentile": (max_stats.get("stats") or {}).get("current_percentile"),
            "span_years": (max_stats.get("stats") or {}).get("span_years"),
            "observation_count": (max_stats.get("stats") or {}).get("observation_count"),
        } if max_stats.get("ok") else None,
        "confidence": stats.get("confidence") or "LOW",
        "statistics": stats if stats.get("ok") else stats,
        "windows_supported": list(WINDOWS),
        "data_sources": [
            "daily_market_history (Yahoo / NSE / Upstox prices)",
            "financials_annual / financials_quarterly (statements)",
            "corporate_actions (dividends / splits)",
            "warehouse_reconstruction (point-in-time multiples)",
            "valuation_policy (Phase 8.2A applicability)",
        ],
        "vendor_historical_ratios": False,
    }
