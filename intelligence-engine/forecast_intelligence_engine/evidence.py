"""Warehouse + engine evidence loader. FIE never calls vendors."""

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


def _safe(fn) -> Optional[dict[str, Any]]:
    try:
        out = fn()
        return out if isinstance(out, dict) else {"value": out}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def load_bundle(symbol: str) -> dict[str, Any]:
    """Gather FIE inputs. Soft-fails per engine. Never invents values."""
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
    hist_val = sorted(
        _rows("historical_valuation", ticker, limit=200),
        key=lambda r: str(r.get("date") or ""),
    )
    hist_stats = _rows("historical_statistics", ticker, limit=80)
    ratios = _rows("valuation_ratios", ticker, limit=20)
    ownership = _rows("ownership", ticker, limit=20)
    actions = _rows("corporate_actions", ticker, limit=80)
    timeline = _rows("research_timeline", ticker, limit=100)
    consensus = _rows("consensus", ticker, limit=100)
    forecast_hist = sorted(
        _rows("forecast_history", ticker, limit=100),
        key=lambda r: str(r.get("as_of") or r.get("generated_at") or ""),
    )
    forecast_acc = _rows("forecast_accuracy", ticker, limit=40)

    uve = _safe(
        lambda: __import__("valuation_engine", fromlist=["get_company_valuation"]).get_company_valuation(ticker)
    )
    vpae = _safe(lambda: __import__("valuation_policy", fromlist=["evaluate"]).evaluate(ticker))
    hvie = _safe(
        lambda: __import__(
            "historical_valuation_intelligence.production", fromlist=["company"]
        ).company(ticker, window="max")
    )
    varie = _safe(
        lambda: __import__("valuation_attribution_engine", fromlist=["company"]).company(ticker, window="10y")
    )
    rie = _safe(
        lambda: __import__("research_intelligence_engine", fromlist=["company"]).company(ticker)
    )
    # Phase 9.0 — FIE consumes MIE top-down context (regime / scenarios / sector impact).
    mie = _safe(
        lambda: __import__("macro_intelligence_engine", fromlist=["module"]).module(
            "regime", country="India"
        )
    )
    mie_scenarios = _safe(
        lambda: __import__("macro_intelligence_engine", fromlist=["scenarios"]).scenarios("India")
    )

    latest_annual = annual[-1] if annual else {}
    prev_annual = annual[-2] if len(annual) >= 2 else {}
    annual_periods = {
        str(row.get("fiscal_year") or "").strip().upper()
        for row in annual
        if row.get("fiscal_year")
    }
    quarterly_periods = {
        str(row.get("fiscal_period") or "").strip().upper()
        for row in quarterly
        if row.get("fiscal_period")
    }
    required_history = {
        "revenue_observations": sum(metric(row, "revenue") is not None for row in annual),
        "pat_observations": sum(metric(row, "pat", "net_income") is not None for row in annual),
        "annual_periods": len(annual_periods),
        "quarterly_periods": len(quarterly_periods),
    }
    readiness_failures = []
    if required_history["annual_periods"] < 2:
        readiness_failures.append("annual_history_below_2_periods")
    if required_history["quarterly_periods"] < 8:
        readiness_failures.append("quarterly_history_below_8_periods")
    if required_history["revenue_observations"] < 2:
        readiness_failures.append("revenue_history_below_2_observations")
    if required_history["pat_observations"] < 2:
        readiness_failures.append("pat_history_below_2_observations")

    return {
        "symbol": ticker,
        "master": master,
        "annual": annual,
        "quarterly": quarterly,
        "historical_valuation": hist_val,
        "historical_statistics": hist_stats,
        "valuation_ratios": ratios,
        "ownership": ownership,
        "corporate_actions": actions,
        "research_timeline": timeline,
        "consensus": consensus,
        "forecast_history": forecast_hist,
        "forecast_accuracy": forecast_acc,
        "latest_annual": latest_annual,
        "prev_annual": prev_annual,
        "data_readiness": {
            **required_history,
            "forecast_ready": not readiness_failures,
            "failures": readiness_failures,
            "policy": "verified_warehouse_facts_only",
        },
        "uve": uve or {},
        "vpae": vpae or {},
        "hvie": hvie or {},
        "varie": varie or {},
        "rie": rie or {},
        "mie": mie or {},
        "mie_scenarios": mie_scenarios or {},
        "inputs_present": {
            "master": bool(master.get("symbol") or master.get("company_name")),
            "financials_annual": len(annual) >= 2,
            "financials_quarterly": len(quarterly) > 0,
            "historical_valuation": len(hist_val) > 0,
            "uve": bool(uve and uve.get("ok") is not False),
            "hvie": bool(hvie and hvie.get("ok")),
            "varie": bool(varie and varie.get("ok")),
            "vpae": bool(vpae and (vpae.get("ok") or vpae.get("primary_model"))),
            "rie": bool(rie and rie.get("ok")),
            "mie": bool(mie and mie.get("ok") is not False and not mie.get("error")),
        },
    }


def metric(row: dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = _num(row.get(k))
        if v is not None:
            return v
    return None


def cagr(values: list[Optional[float]], years: Optional[float] = None) -> Optional[float]:
    """Compound annual growth between first and last non-null values."""
    clean = [v for v in values if v is not None and v > 0]
    if len(clean) < 2:
        return None
    n = years if years is not None else float(len(clean) - 1)
    if n <= 0:
        return None
    try:
        return (clean[-1] / clean[0]) ** (1.0 / n) - 1.0
    except Exception:
        return None


def series_field(rows: list[dict[str, Any]], *keys: str) -> list[Optional[float]]:
    out: list[Optional[float]] = []
    for r in rows:
        out.append(metric(r, *keys))
    return out
