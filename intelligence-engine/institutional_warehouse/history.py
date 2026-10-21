"""Historical read API over the existing warehouse tabs.

No new schemas: these are query shapes over the tables Phase 7.0 already
created. Date range, rolling window, fiscal year, quarter, latest and
as-at-a-date, plus the series shape a chart needs.

Aggregates are computed here at query time rather than stored, so a CAGR always
reflects the current contents of the warehouse instead of a stale derived row.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from institutional_warehouse import db, store
from institutional_warehouse.schema import find_tab
from institutional_warehouse.values import normalise_entity, to_date, to_number

# Which tab and column answer "history of X".
SERIES: dict[str, dict[str, Any]] = {
    "price": {"tab": "daily_market_history", "period": "date", "field": "close"},
    "adjusted_price": {"tab": "daily_market_history", "period": "date", "field": "adjusted_close"},
    "volume": {"tab": "daily_market_history", "period": "date", "field": "volume"},
    "market_cap": {"tab": "historical_valuation", "period": "date", "field": "market_cap"},
    "enterprise_value": {"tab": "historical_valuation", "period": "date", "field": "enterprise_value"},
    "pe": {"tab": "historical_valuation", "period": "date", "field": "pe"},
    "pb": {"tab": "historical_valuation", "period": "date", "field": "pb"},
    "ev_ebitda": {"tab": "historical_valuation", "period": "date", "field": "ev_ebitda"},
    "ev_sales": {"tab": "historical_valuation", "period": "date", "field": "ev_sales"},
    "price_sales": {"tab": "historical_valuation", "period": "date", "field": "price_sales"},
    "dividend_yield": {"tab": "historical_valuation", "period": "date", "field": "dividend_yield"},
    # Point-in-time profitability reconstructed onto historical_valuation (Phase 8.3B).
    # Annual statement ratios remain available via historical_ratios for fiscal charts.
    "valuation_roe": {"tab": "historical_valuation", "period": "date", "field": "roe"},
    "valuation_roce": {"tab": "historical_valuation", "period": "date", "field": "roce"},
    "valuation_roa": {"tab": "historical_valuation", "period": "date", "field": "roa"},
    "revenue": {"tab": "financials_annual", "period": "fiscal_year", "field": "revenue"},
    "ebitda": {"tab": "financials_annual", "period": "fiscal_year", "field": "ebitda"},
    "pat": {"tab": "financials_annual", "period": "fiscal_year", "field": "pat"},
    "eps": {"tab": "financials_annual", "period": "fiscal_year", "field": "eps"},
    "equity": {"tab": "financials_annual", "period": "fiscal_year", "field": "equity"},
    "debt": {"tab": "financials_annual", "period": "fiscal_year", "field": "debt"},
    "cash": {"tab": "financials_annual", "period": "fiscal_year", "field": "cash"},
    "free_cash_flow": {"tab": "financials_annual", "period": "fiscal_year", "field": "free_cash_flow"},
    "roe": {"tab": "historical_ratios", "period": "period", "field": "roe",
             "filters": {"basis": "annual"}},
    "roce": {"tab": "historical_ratios", "period": "period", "field": "roce",
             "filters": {"basis": "annual"}},
    "roa": {"tab": "historical_ratios", "period": "period", "field": "roa",
             "filters": {"basis": "annual"}},
    "net_margin": {"tab": "historical_ratios", "period": "period", "field": "net_margin",
             "filters": {"basis": "annual"}},
    "ebitda_margin": {"tab": "historical_ratios", "period": "period", "field": "ebitda_margin",
             "filters": {"basis": "annual"}},
    "debt_equity": {"tab": "historical_ratios", "period": "period", "field": "debt_equity",
             "filters": {"basis": "annual"}},
    "revenue_quarterly": {"tab": "financials_quarterly", "period": "fiscal_period", "field": "revenue"},
    "pat_quarterly": {"tab": "financials_quarterly", "period": "fiscal_period", "field": "pat"},
    "target_price": {"tab": "consensus", "period": "consensus_date", "field": "target_price"},
    "promoter_holding": {"tab": "ownership", "period": "as_of", "field": "promoter_holding"},
    "fii": {"tab": "ownership", "period": "as_of", "field": "fii"},
}

WINDOWS = {
    "1y": 365,
    "3y": 1095,
    "5y": 1826,
    "10y": 3652,
    "15y": 5479,
    "20y": 7305,
    "max": None,
}


def _window_floor(window: Optional[str]) -> Optional[str]:
    days = WINDOWS.get(str(window or "max").lower(), None)
    if not days:
        return None
    return (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()


def _rows(tab_id: str, symbol: str, limit: int = 20000,
          filters: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    rows = store.all_rows(tab_id, entity=symbol, limit=limit)
    if not filters:
        return rows
    # Ratio tabs hold annual and quarterly rows side by side. Interleaving them
    # produces a series that alternates between two different measures.
    return [r for r in rows if all(str(r.get(k)) == str(v) for k, v in filters.items())]


def series(
    symbol: str,
    metric: str,
    *,
    window: Optional[str] = "max",
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 5000,
) -> dict[str, Any]:
    """One metric through time for one company."""
    ticker = normalise_entity(symbol)
    spec = SERIES.get(str(metric or "").strip().lower())
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}
    if not spec:
        return {"ok": False, "error": f"unknown_metric:{metric}", "available": sorted(SERIES)}

    floor = start or _window_floor(window)
    points = []
    for row in _rows(spec["tab"], ticker, filters=spec.get("filters")):
        period = str(row.get(spec["period"]) or "")
        value = to_number(row.get(spec["field"]))
        if not period or value is None:
            continue
        as_date = to_date(period)
        if as_date:
            if floor and as_date < floor:
                continue
            if end and as_date > end:
                continue
        points.append({"period": period, "value": value, "source": row.get("source")})

    points.sort(key=lambda p: str(p["period"]))
    points = points[-max(1, int(limit)):]
    return {
        "ok": True,
        "symbol": ticker,
        "metric": metric,
        "tab": spec["tab"],
        "window": window,
        "points": points,
        "count": len(points),
        "first": points[0]["period"] if points else None,
        "last": points[-1]["period"] if points else None,
        **_aggregates(points),
    }


def _aggregates(points: list[dict[str, Any]]) -> dict[str, Any]:
    """Computed here, never stored: the warehouse keeps observations, not trends."""
    values = [p["value"] for p in points if p.get("value") is not None]
    if not values:
        return {"stats": None}
    first, last = values[0], values[-1]
    span_years = _span_years(points)
    cagr = None
    if first > 0 and last > 0 and span_years and span_years >= 1:
        cagr = round(((last / first) ** (1.0 / span_years) - 1.0) * 100.0, 2)
    ordered = sorted(values)
    mid = len(ordered) // 2
    median = ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    current_percentile = round(100.0 * sum(1 for v in values if v <= last) / len(values), 1)
    return {
        "stats": {
            "first": first,
            "last": last,
            "min": min(values),
            "max": max(values),
            "median": round(median, 4),
            "average": round(sum(values) / len(values), 4),
            "change_pct": round(100.0 * (last - first) / first, 2) if first else None,
            "cagr_pct": cagr,
            "years": span_years,
            "current_percentile": current_percentile,
        }
    }


def _span_years(points: list[dict[str, Any]]) -> Optional[float]:
    dates = [to_date(p["period"]) for p in points]
    dates = [d for d in dates if d]
    if len(dates) >= 2:
        delta = datetime.fromisoformat(dates[-1]) - datetime.fromisoformat(dates[0])
        return round(delta.days / 365.25, 2)
    periods = [str(p["period"]) for p in points]
    if len(periods) >= 2 and periods[0].startswith("FY"):
        return float(len(periods) - 1)
    return None


def company_history(
    symbol: str,
    *,
    window: Optional[str] = "max",
    metrics: Optional[Iterable[str]] = None,
) -> dict[str, Any]:
    ticker = normalise_entity(symbol)
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}
    wanted = list(metrics) if metrics else ["price", "revenue", "pat", "eps", "roe", "pe", "pb"]
    return {
        "ok": True,
        "symbol": ticker,
        "window": window,
        "series": {m: series(ticker, m, window=window) for m in wanted if m in SERIES},
        "available_metrics": sorted(SERIES),
    }


def as_at(symbol: str, on: str) -> dict[str, Any]:
    """What the warehouse knew about a company on a given date."""
    ticker = normalise_entity(symbol)
    observed = to_date(on)
    if not ticker or not observed:
        return {"ok": False, "error": "symbol_and_date_required"}

    def _latest(tab_id: str, period: str) -> Optional[dict[str, Any]]:
        rows = [r for r in _rows(tab_id, ticker)
                if to_date(r.get(period)) and to_date(r.get(period)) <= observed]
        if not rows:
            return None
        return sorted(rows, key=lambda r: str(to_date(r.get(period))))[-1]

    return {
        "ok": True,
        "symbol": ticker,
        "as_at": observed,
        "price": _latest("daily_market_history", "date"),
        "valuation": _latest("historical_valuation", "date"),
        "consensus": _latest("consensus", "consensus_date"),
        "ownership": _latest("ownership", "as_of"),
    }


def range_query(
    tab_id: str,
    *,
    symbol: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    fiscal_year: Optional[str] = None,
    quarter: Optional[str] = None,
    window: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
) -> dict[str, Any]:
    """Date range, fiscal year, quarter or rolling window over any historical tab."""
    tab = find_tab(tab_id)
    if not tab:
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    period = next((k for k in tab.key if k != tab.entity_column), None)
    if not period:
        return {"ok": False, "error": f"tab_has_no_period:{tab_id}"}

    filters: dict[str, Any] = {}
    if fiscal_year and tab.column("fiscal_year"):
        filters["fiscal_year"] = fiscal_year
    if quarter and tab.column("quarter"):
        filters["quarter"] = quarter

    floor = start or _window_floor(window) if (start or window) else None
    rows = store.fetch(tab.id, entity=symbol, filters=filters, sort=period, order="desc",
                       limit=max(1, min(int(limit), 5000)), offset=max(0, int(offset)))
    kept = []
    for row in rows["rows"]:
        value = to_date(row.get(period)) or str(row.get(period) or "")
        if floor and value and value < floor:
            continue
        if end and value and value > end:
            continue
        kept.append(row)
    return {
        "ok": True,
        "tab": tab.id,
        "period_column": period,
        "symbol": symbol,
        "total": rows["total"],
        "returned": len(kept),
        "rows": kept,
    }


def compare(
    symbols: Iterable[str],
    metric: str,
    *,
    window: Optional[str] = "5y",
) -> dict[str, Any]:
    """The same metric, the same window, several companies."""
    names = [normalise_entity(s) for s in symbols if normalise_entity(s)]
    if not names:
        return {"ok": False, "error": "no_symbols"}
    if metric not in SERIES:
        return {"ok": False, "error": f"unknown_metric:{metric}", "available": sorted(SERIES)}
    out = {name: series(name, metric, window=window) for name in names}
    ranked = sorted(
        [
            {"symbol": name, "last": (payload.get("stats") or {}).get("last"),
             "cagr_pct": (payload.get("stats") or {}).get("cagr_pct"),
             "points": payload.get("count")}
            for name, payload in out.items()
        ],
        key=lambda entry: (entry["cagr_pct"] is None, -(entry["cagr_pct"] or 0)),
    )
    return {"ok": True, "metric": metric, "window": window, "series": out, "ranking": ranked}


def coverage(symbol: str) -> dict[str, Any]:
    """How much history exists for one company, tab by tab."""
    ticker = normalise_entity(symbol)
    if not ticker:
        return {"ok": False, "error": "empty_symbol"}
    out: dict[str, Any] = {}
    for tab_id, period in (
        ("daily_market_history", "date"),
        ("financials_annual", "fiscal_year"),
        ("financials_quarterly", "fiscal_period"),
        ("historical_valuation", "date"),
        ("historical_ratios", "period"),
        ("consensus", "consensus_date"),
        ("ownership", "as_of"),
        ("corporate_actions", "action_date"),
        ("research_timeline", "date"),
    ):
        table = db.physical_table(tab_id)
        row = db.query(
            f'SELECT COUNT(*) AS n, MIN("{period}") AS a, MAX("{period}") AS b'
            f" FROM {table} WHERE sys_entity = ?",
            (ticker,),
        )[0]
        out[tab_id] = {"rows": int(row.get("n") or 0), "first": row.get("a"), "last": row.get("b")}
    price = out["daily_market_history"]
    years = 0.0
    if price["first"] and price["last"]:
        try:
            delta = datetime.fromisoformat(str(price["last"])) - datetime.fromisoformat(str(price["first"]))
            years = round(delta.days / 365.25, 2)
        except Exception:
            years = 0.0
    return {"ok": True, "symbol": ticker, "price_years": years, "tabs": out}
