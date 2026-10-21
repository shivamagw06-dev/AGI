"""Extract structured institutional knowledge from gathered packs / HD series.

This is NOT ML model training. It materialises trends, metrics, and themes
that analyst agents can consume on future runs.
"""

from __future__ import annotations

import math
from typing import Any

from continuous_gather_learn import persist as cgl_persist


def _num(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _cagr(first: float | None, last: float | None, years: float) -> float | None:
    if first is None or last is None or first <= 0 or last <= 0 or years <= 0:
        return None
    try:
        return round((math.pow(last / first, 1.0 / years) - 1.0) * 100.0, 4)
    except Exception:
        return None


def extract_from_hd_pack(pack: dict[str, Any] | None, *, entity: str) -> dict[str, Any]:
    """Soft extraction from a Historical Depth / company pack."""
    pack = pack if isinstance(pack, dict) else {}
    financials = pack.get("financials") or pack.get("financial_history") or {}
    prices = pack.get("prices") or pack.get("ohlcv") or pack.get("market_history") or {}
    narrative = pack.get("narrative") or pack.get("summary") or {}

    metrics: dict[str, Any] = {
        "revenue_cagr": _num(financials.get("revenue_cagr") or financials.get("sales_cagr")),
        "ebitda_cagr": _num(financials.get("ebitda_cagr")),
        "margin_trend": financials.get("margin_trend") or financials.get("operating_margin_trend"),
        "debt_trend": financials.get("debt_trend"),
        "roe_history": financials.get("roe_history") or financials.get("roe"),
        "roce_history": financials.get("roce_history") or financials.get("roce"),
        "cash_conversion": financials.get("cash_conversion"),
        "avg_return": _num(prices.get("avg_return") or prices.get("mean_return")),
        "volatility": _num(prices.get("volatility") or prices.get("stdev")),
        "max_drawdown": _num(prices.get("max_drawdown") or prices.get("drawdown")),
        "beta": _num(prices.get("beta")),
    }
    themes = list(pack.get("themes") or narrative.get("themes") or [])[:12]
    risks = list(pack.get("risks") or narrative.get("risks") or [])[:8]
    catalysts = list(pack.get("catalysts") or [])[:8]

    out = {
        "entity": entity,
        "kind": "structured_knowledge_extract",
        "metrics": {k: v for k, v in metrics.items() if v is not None},
        "themes": themes,
        "risks": risks,
        "catalysts": catalysts,
        "provenance": {
            "source": "knowledge_factory_historical_depth",
            "keys_seen": sorted(list(pack.keys())[:40]),
        },
        "learning_mode": "structured_extraction_not_ml_training",
    }
    cgl_persist.put_knowledge_extract(entity, out)
    return out


def extract_from_hd_series(entity: str) -> dict[str, Any]:
    """Compute financial / price intelligence directly from HD store series."""
    from knowledge_factory.historical_depth import store as hd_store

    e = entity.upper()
    annual = list((hd_store.get_series("financials_annual", e) or {}).get("records") or [])
    prices = list((hd_store.get_series("prices", e) or {}).get("records") or [])
    actions = list((hd_store.get_series("corporate_actions", e) or {}).get("records") or [])
    derived = hd_store.get_object("derived", e) or hd_store.get_report(f"derived_{e}") or {}

    rev = [_num((r.get("payload") or {}).get("revenue")) for r in annual]
    rev = [v for v in rev if v is not None]
    ni = [_num((r.get("payload") or {}).get("net_income")) for r in annual]
    ni = [v for v in ni if v is not None]
    debt = [_num((r.get("payload") or {}).get("total_debt")) for r in annual]
    debt = [v for v in debt if v is not None]
    years = max(1.0, float(len(annual) - 1)) if len(annual) > 1 else float(max(len(rev) - 1, 1))

    closes = []
    for r in prices:
        p = r.get("payload") or {}
        c = _num(p.get("price") if p.get("price") is not None else p.get("close"))
        if c is not None:
            closes.append(c)

    # Returns / vol / drawdown
    rets = []
    for i in range(1, len(closes)):
        if closes[i - 1]:
            rets.append((closes[i] / closes[i - 1]) - 1.0)
    avg_ret = (sum(rets) / len(rets)) if rets else None
    vol = None
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        var = sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)
        vol = math.sqrt(var)
    max_dd = None
    if closes:
        peak = closes[0]
        dd = 0.0
        for c in closes:
            peak = max(peak, c)
            if peak > 0:
                dd = min(dd, c / peak - 1.0)
        max_dd = dd

    long_term_return = None
    if len(closes) >= 2 and closes[0]:
        long_term_return = (closes[-1] / closes[0]) - 1.0

    roe_pts = []
    try:
        from knowledge_factory.historical_depth.producers.derived import produce_derived

        d = produce_derived(e)
        roe_meta = ((d or {}).get("metrics") or {}).get("ROE") or {}
        pts = roe_meta.get("points") if isinstance(roe_meta, dict) else None
        if isinstance(pts, dict):
            roe_pts = list(pts.values())[:20]
    except Exception:
        roe_pts = []

    debt_trend = None
    if len(debt) >= 2:
        debt_trend = "rising" if debt[-1] > debt[0] else ("falling" if debt[-1] < debt[0] else "flat")

    metrics = {
        "revenue_cagr": _cagr(rev[0], rev[-1], years) if len(rev) >= 2 else None,
        "earnings_cagr": _cagr(ni[0], ni[-1], years) if len(ni) >= 2 else None,
        "debt_trend": debt_trend,
        "roe_history": roe_pts or None,
        "avg_return": round(avg_ret, 6) if avg_ret is not None else None,
        "volatility": round(vol, 6) if vol is not None else None,
        "max_drawdown": round(max_dd, 6) if max_dd is not None else None,
        "long_term_return": round(long_term_return, 6) if long_term_return is not None else None,
        "price_points": len(closes),
        "annual_periods": len(annual),
        "corporate_actions": len(actions),
    }

    # Narrative hooks from timeline
    timeline = list((hd_store.get_series("timeline", e) or {}).get("records") or [])
    risks = []
    themes = []
    for ev in timeline[-12:]:
        payload = ev.get("payload") or ev
        title = str(payload.get("title") or payload.get("event_type") or "")
        et = str(payload.get("event_type") or ev.get("kind") or "").lower()
        if any(k in et for k in ("risk", "litigation", "regulatory")):
            risks.append(title[:120])
        elif title:
            themes.append(title[:120])

    out = {
        "entity": e,
        "kind": "structured_knowledge_extract",
        "metrics": {k: v for k, v in metrics.items() if v is not None},
        "themes": themes[:12],
        "risks": risks[:8],
        "catalysts": [],
        "provenance": {
            "source": "hd_series_compute",
            "annual": len(annual),
            "prices": len(prices),
            "actions": len(actions),
            "derived_keys": list(derived.keys())[:20] if isinstance(derived, dict) else [],
        },
        "learning_mode": "structured_extraction_not_ml_training",
    }
    cgl_persist.put_knowledge_extract(e, out)
    return out


def extract_batch_from_daily_report(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Walk a KF daily / HD report and extract per-entity knowledge when present."""
    report = report if isinstance(report, dict) else {}
    out: list[dict[str, Any]] = []
    entities = (
        report.get("entities")
        or report.get("tickers")
        or report.get("updated_entities")
        or []
    )
    packs = report.get("packs") or report.get("entity_packs") or {}
    rows = report.get("rows") or []
    if isinstance(entities, dict):
        entities = list(entities.keys())
    if isinstance(entities, int):
        # pipeline reports entities as count — prefer rows
        entities = [r.get("entity") for r in rows if isinstance(r, dict) and r.get("entity")]
    for ent in list(entities)[:40]:
        key = str(ent)
        pack = packs.get(key) if isinstance(packs, dict) else None
        if not isinstance(pack, dict):
            try:
                out.append(extract_from_hd_series(key))
                continue
            except Exception:
                pack = {"summary": report.get("summary") or {}}
        out.append(extract_from_hd_pack(pack, entity=key))
    if not out and rows:
        for r in rows[:40]:
            if isinstance(r, dict) and r.get("entity"):
                try:
                    out.append(extract_from_hd_series(str(r["entity"])))
                except Exception:
                    continue
    if not out and report:
        out.append(
            extract_from_hd_pack(
                {"summary": report.get("summary") or report.get("status")},
                entity=str(report.get("universe") or "UNIVERSE"),
            )
        )
    return out
