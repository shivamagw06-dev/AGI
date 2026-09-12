"""Warehouse + engine evidence loader. RIE never calls vendors."""

from __future__ import annotations

from typing import Any, Optional


def _num(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        f = float(v)
        if f != f:
            return None
        return f
    except Exception:
        return None


def _rows(tab: str, symbol: str, *, limit: int = 200) -> list[dict[str, Any]]:
    try:
        from institutional_warehouse import store

        page = store.fetch(tab, entity=str(symbol).upper(), limit=limit)
        return list(page.get("rows") or [])
    except Exception:
        try:
            from institutional_warehouse import store

            return list(store.all_rows(tab, entity=str(symbol).upper(), limit=limit) or [])
        except Exception:
            return []


def _master(symbol: str) -> dict[str, Any]:
    rows = _rows("company_master", symbol, limit=1)
    if rows:
        return rows[0]
    try:
        from institutional_warehouse import store

        page = store.fetch("company_master", filters={"symbol": str(symbol).upper()}, limit=1)
        return (page.get("rows") or [{}])[0] if page.get("rows") else {}
    except Exception:
        return {}


def load_bundle(symbol: str) -> dict[str, Any]:
    """Gather all RIE inputs for one company. Soft-fails per engine."""
    ticker = str(symbol or "").strip().upper()
    master = _master(ticker)
    annual = sorted(
        _rows("financials_annual", ticker, limit=40),
        key=lambda r: str(r.get("fiscal_year") or r.get("period") or ""),
    )
    quarterly = sorted(
        _rows("financials_quarterly", ticker, limit=40),
        key=lambda r: str(r.get("fiscal_period") or r.get("period") or ""),
    )
    ownership = sorted(
        _rows("ownership", ticker, limit=40),
        key=lambda r: str(r.get("as_of") or r.get("date") or ""),
    )
    actions = sorted(
        _rows("corporate_actions", ticker, limit=100),
        key=lambda r: str(r.get("date") or ""),
    )
    ratios = _rows("valuation_ratios", ticker, limit=20)
    hist_val = sorted(
        _rows("historical_valuation", ticker, limit=200),
        key=lambda r: str(r.get("date") or ""),
    )
    hist_stats = _rows("historical_statistics", ticker, limit=80)
    timeline = sorted(
        _rows("research_timeline", ticker, limit=200),
        key=lambda r: str(r.get("date") or ""),
    )
    research_docs = _rows("research_intelligence", ticker, limit=40)

    uve = _safe(lambda: __import__("valuation_engine", fromlist=["get_company_valuation"]).get_company_valuation(ticker))
    vpae = _safe(lambda: __import__("valuation_policy", fromlist=["evaluate"]).evaluate(ticker))
    hvie = _safe(
        lambda: __import__(
            "historical_valuation_intelligence.production", fromlist=["company"]
        ).company(ticker, window="max")
    )
    varie = _safe(
        lambda: __import__(
            "valuation_attribution_engine", fromlist=["company"]
        ).company(ticker, window="10y")
    )
    ownership_intel = _safe(
        lambda: __import__(
            "ownership_intelligence.production", fromlist=["analyse"]
        ).analyse(ticker)
    )

    latest_annual = annual[-1] if annual else {}
    prev_annual = annual[-2] if len(annual) >= 2 else {}
    latest_ratio = ratios[0] if ratios else {}
    latest_own = ownership[-1] if ownership else {}

    return {
        "symbol": ticker,
        "master": master,
        "annual": annual,
        "quarterly": quarterly,
        "ownership": ownership,
        "corporate_actions": actions,
        "valuation_ratios": ratios,
        "historical_valuation": hist_val,
        "historical_statistics": hist_stats,
        "research_timeline": timeline,
        "research_documents": research_docs,
        "latest_annual": latest_annual,
        "prev_annual": prev_annual,
        "latest_ratio": latest_ratio,
        "latest_ownership": latest_own,
        "uve": uve or {},
        "vpae": vpae or {},
        "hvie": hvie or {},
        "varie": varie or {},
        "ownership_intel": ownership_intel or {},
        "inputs_present": {
            "master": bool(master.get("symbol") or master.get("company_name")),
            "financials_annual": len(annual) > 0,
            "financials_quarterly": len(quarterly) > 0,
            "ownership": len(ownership) > 0,
            "corporate_actions": len(actions) > 0,
            "valuation_ratios": len(ratios) > 0,
            "historical_valuation": len(hist_val) > 0,
            "uve": bool(uve and uve.get("ok") is not False and (uve.get("valuation") or uve.get("primary") or uve.get("metrics"))),
            "hvie": bool(hvie and hvie.get("ok")),
            "varie": bool(varie and varie.get("ok")),
            "vpae": bool(vpae and (vpae.get("ok") or vpae.get("primary_model") or vpae.get("primary_metric"))),
        },
    }


def _safe(fn) -> Optional[dict[str, Any]]:
    try:
        out = fn()
        return out if isinstance(out, dict) else {"value": out}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def growth_pct(curr: Any, prev: Any) -> Optional[float]:
    c, p = _num(curr), _num(prev)
    if c is None or p is None or p == 0:
        return None
    return round(100.0 * (c - p) / abs(p), 2)


def series_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    out = []
    for r in rows:
        v = _num(r.get(field))
        if v is not None:
            out.append(v)
    return out


def metric(row: dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = _num(row.get(k))
        if v is not None:
            return v
    return None
