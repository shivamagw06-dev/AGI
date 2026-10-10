"""Persist HVIE rolling statistics and sector medians (weekly job)."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from historical_valuation_intelligence.models import ENGINE_CODE, METRICS, VERSION, WINDOWS


def persist_company_statistics(
    symbol: str,
    *,
    metrics: Optional[list[str]] = None,
    actor: str = "hvie_runtime",
) -> dict[str, Any]:
    """Compute + append statistics rows for one company across all windows."""
    from institutional_warehouse import gateway
    from historical_valuation_intelligence.engine import statistics_for

    ticker = str(symbol or "").strip().upper()
    as_of = date.today().isoformat()
    wanted = metrics or ["pe", "pb", "ev_ebitda", "ev_sales", "dividend_yield"]
    rows: list[dict[str, Any]] = []
    for metric in wanted:
        pack = statistics_for(ticker, metric=metric)
        if not pack.get("ok"):
            continue
        for window, stats in (pack.get("windows") or {}).items():
            if not stats.get("ok"):
                continue
            regime = (pack.get("regime") or {}).get("regime") if window == "max" else None
            if window != "max":
                from historical_valuation_intelligence.statistics import regime_from_percentile

                regime = regime_from_percentile(stats.get("current_percentile")).get("regime")
            rows.append({
                "symbol": ticker,
                "metric": metric,
                "window": window,
                "as_of": as_of,
                "observation_count": stats.get("observation_count"),
                "min_value": stats.get("min"),
                "max_value": stats.get("max"),
                "mean_value": stats.get("mean"),
                "median_value": stats.get("median"),
                "stdev": stats.get("stdev"),
                "p25": stats.get("p25"),
                "p75": stats.get("p75"),
                "current_value": stats.get("current"),
                "current_percentile": stats.get("current_percentile"),
                "z_score": stats.get("z_score"),
                "premium_to_median_pct": stats.get("premium_to_median_pct"),
                "span_years": stats.get("span_years"),
                "regime": regime,
                "confidence": pack.get("confidence"),
            })
    written = {"ok": True, "written": 0}
    if rows:
        written = gateway.write(
            "historical_statistics", rows, source=ENGINE_CODE, actor=actor,
            reason=f"hvie_weekly_stats:{ticker}",
        )
    return {
        "ok": True,
        "symbol": ticker,
        "rows": len(rows),
        "written": written,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def persist_sector_medians(
    *,
    as_of: Optional[str] = None,
    metric: str = "pe",
    actor: str = "hvie_runtime",
) -> dict[str, Any]:
    """Cross-sectional sector medians from latest historical_valuation rows."""
    import statistics
    from collections import defaultdict

    from institutional_warehouse import gateway, store

    observed = as_of or date.today().isoformat()
    masters = {
        str(r.get("symbol") or "").upper(): r
        for r in (store.all_rows("company_master", limit=6000) or [])
    }
    # Latest observation per symbol (scan recent valuation rows).
    latest: dict[str, dict[str, Any]] = {}
    for row in store.all_rows("historical_valuation", limit=20000) or []:
        sym = str(row.get("symbol") or "").upper()
        if not sym:
            continue
        prev = latest.get(sym)
        if not prev or str(row.get("date") or "") > str(prev.get("date") or ""):
            latest[sym] = row

    # Institutional bounds — do not persist near-zero / absurd multiples.
    sane = {
        "pe": (2.0, 250.0),
        "pb": (0.05, 60.0),
        "ev_ebitda": (1.0, 100.0),
        "ev_sales": (0.2, 80.0),
    }.get(str(metric or "pe").lower(), (0.0, float("inf")))

    buckets: dict[str, list[float]] = defaultdict(list)
    for sym, row in latest.items():
        val = row.get(metric)
        try:
            num = float(val) if val is not None else None
        except (TypeError, ValueError):
            num = None
        if num is None or not (sane[0] <= num <= sane[1]):
            continue
        sector = str((masters.get(sym) or {}).get("sector") or "Unclassified")
        buckets[sector].append(num)

    out_rows = []
    for sector, values in buckets.items():
        if len(values) < 2:
            continue
        out_rows.append({
            "sector": sector,
            "metric": metric,
            "as_of": observed,
            "median_value": round(statistics.median(values), 4),
            "company_count": len(values),
        })
    written = {"ok": True, "written": 0}
    if out_rows:
        written = gateway.write(
            "historical_sector_medians", out_rows, source=ENGINE_CODE, actor=actor,
            reason=f"hvie_weekly_sector_medians:{metric}",
        )
    return {
        "ok": True,
        "as_of": observed,
        "metric": metric,
        "sectors": len(out_rows),
        "written": written,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }
