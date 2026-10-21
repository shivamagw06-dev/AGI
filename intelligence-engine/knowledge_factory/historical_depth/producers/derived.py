"""Historical derived producers — recompute ratios from primitives only."""

from __future__ import annotations

import math
from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.schema import DERIVED_METRICS, HD_VERSION
from knowledge_factory.historical_depth.store import filter_pit


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _derive_row(payload: dict[str, float]) -> dict[str, float | None]:
    price = payload.get("price")
    eps = payload.get("eps")
    bvps = payload.get("bvps")
    shares = payload.get("shares")
    debt = payload.get("total_debt")
    cash = payload.get("cash")
    ebitda = payload.get("ebitda")
    ebit = payload.get("ebit")
    revenue = payload.get("revenue")
    ni = payload.get("net_income")
    equity = payload.get("equity")
    ocf = payload.get("ocf")
    gp = payload.get("gross_profit")
    fcf = payload.get("fcf")

    mkt = (price * shares) if price is not None and shares is not None else None
    ev = (mkt + (debt or 0) - (cash or 0)) if mkt is not None else None
    invested = ((debt or 0) + (equity or 0) - (cash or 0)) if equity is not None else None
    nopat = (ebit * 0.75) if ebit is not None else None

    return {
        "PE": _safe_div(price, eps) if eps and eps > 0 else None,
        "PB": _safe_div(price, bvps) if bvps and bvps > 0 else None,
        "EV_EBITDA": _safe_div(ev, ebitda) if ebitda and ebitda > 0 else None,
        "EV_Sales": _safe_div(ev, revenue) if revenue and revenue > 0 else None,
        "ROIC": _safe_div(nopat, invested) * 100.0 if nopat is not None and invested and invested > 0 else None,
        "ROE": _safe_div(ni, equity) * 100.0 if ni is not None and equity and equity > 0 else None,
        "ROA": _safe_div(ni, (equity or 0) + (debt or 0)) * 100.0 if ni is not None else None,
        "Gross_Margin": _safe_div(gp, revenue) * 100.0 if gp is not None and revenue else None,
        "Net_Margin": _safe_div(ni, revenue) * 100.0 if ni is not None and revenue else None,
        "EBIT_Margin": _safe_div(ebit, revenue) * 100.0 if ebit is not None and revenue else None,
        "Cash_Conversion": _safe_div(ocf, ni) if ocf is not None and ni and ni > 0 else None,
        "Debt_Equity": _safe_div(debt, equity) if debt is not None and equity and equity > 0 else None,
        "Net_Debt_EBITDA": _safe_div((debt or 0) - (cash or 0), ebitda) if ebitda and ebitda > 0 else None,
        "FCF": fcf,
    }


def produce_derived(entity: str, *, as_of: str | None = None) -> dict[str, Any]:
    series = hd_store.get_series("financials_annual", entity) or {}
    records = list(series.get("records") or [])
    if as_of:
        records = filter_pit(records, as_of)

    points: dict[str, dict[str, float]] = {m: {} for m in DERIVED_METRICS}
    audit: list[dict[str, Any]] = []
    prev_rev = None
    prev_eps = None
    for r in records:
        payload = r.get("payload") or {}
        derived = _derive_row({k: float(v) for k, v in payload.items() if v is not None})
        fy = r["period"]
        rev = payload.get("revenue")
        eps = payload.get("eps")
        if prev_rev and rev and prev_rev > 0:
            derived["Revenue_Growth"] = (rev / prev_rev - 1.0) * 100.0
        if prev_eps and eps and prev_eps > 0:
            derived["EPS_Growth"] = (eps / prev_eps - 1.0) * 100.0
        prev_rev = rev
        prev_eps = eps
        for m, val in derived.items():
            if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
                continue
            if m in points:
                points[m][fy] = round(float(val), 6)
        audit.append({"period": fy, "available_from": r.get("available_from"), "metrics": {k: derived.get(k) for k in ("PE", "PB", "ROIC", "ROE")}})

    # Percentiles & z-scores on PE history
    pe_vals = list(points.get("PE", {}).values())
    percentiles: dict[str, float] = {}
    zscores: dict[str, float] = {}
    if pe_vals:
        ordered = sorted(pe_vals)
        mean = sum(pe_vals) / len(pe_vals)
        var = sum((x - mean) ** 2 for x in pe_vals) / len(pe_vals)
        std = math.sqrt(var) if var > 0 else 0.0
        for fy, pe in points["PE"].items():
            rank = sum(1 for x in ordered if x <= pe) / len(ordered)
            percentiles[fy] = round(rank * 100.0, 2)
            zscores[fy] = round((pe - mean) / std, 4) if std > 0 else 0.0

    out = {
        "entity": entity.upper(),
        "hd_version": HD_VERSION,
        "as_of": as_of,
        "metrics": {
            m: {
                "points": pts,
                "formula": "recomputed_from_historical_primitives",
                "derived_from": ["price", "eps", "bvps", "ebitda", "ebit", "equity", "debt", "cash", "shares", "revenue"],
                "reproducible": True,
            }
            for m, pts in points.items()
            if pts
        },
        "pe_percentiles": percentiles,
        "pe_zscores": zscores,
        "audit": audit,
        "n_periods": len(records),
    }
    hd_store.put_series(
        "derived",
        entity,
        [
            {
                "entity": entity.upper(),
                "kind": "derived_snapshot",
                "period": as_of or "latest",
                "period_end": as_of or "latest",
                "available_from": as_of or "9999-12-31",
                "payload": out,
            }
        ],
    )
    return out


def produce_risk_momentum(entity: str, *, as_of: str | None = None) -> dict[str, Any]:
    series = hd_store.get_series("prices", entity) or {}
    records = list(series.get("records") or [])
    if as_of:
        records = filter_pit(records, as_of)
    if not records:
        return {"entity": entity.upper(), "found": False, "reason": "no_price_history"}

    rets = [float((r.get("payload") or {}).get("return_pct") or 0.0) for r in records]
    closes = [float((r.get("payload") or {}).get("adj_close") or 0.0) for r in records]

    # Max drawdown
    peak = closes[0]
    max_dd = 0.0
    dd_start = records[0].get("period_end")
    dd_trough = records[0].get("period_end")
    peak_date = records[0].get("period_end")
    for r, c in zip(records, closes):
        if c > peak:
            peak = c
            peak_date = r.get("period_end")
        dd = (c / peak - 1.0) if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
            dd_start = peak_date
            dd_trough = r.get("period_end")

    # Momentum 12m ≈ last 12 returns
    mom_12 = sum(rets[-12:]) if len(rets) >= 12 else sum(rets)
    vol = 0.0
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        vol = math.sqrt(sum((x - mean) ** 2 for x in rets) / len(rets))

    return {
        "entity": entity.upper(),
        "found": True,
        "as_of": as_of,
        "n_months": len(records),
        "max_drawdown_pct": round(max_dd * 100.0, 4),
        "drawdown_peak": dd_start,
        "drawdown_trough": dd_trough,
        "momentum_12m_pct": round(mom_12, 4),
        "monthly_vol_pct": round(vol, 4),
        "latest_price": closes[-1],
        "history_start": records[0].get("period_end"),
        "history_end": records[-1].get("period_end"),
    }
