"""Historical trend + statement projection helpers (deterministic)."""

from __future__ import annotations

from typing import Any, Optional

from forecast_intelligence_engine.evidence import cagr, metric, series_field
from forecast_intelligence_engine.models import (
    MIN_ANNUAL_OBS,
    SCENARIO_GROWTH_MULT,
    SCENARIO_MARGIN_DELTA_PP,
    WINDOWS,
)


def _pct(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    return round(100.0 * x, 2)


def _round(x: Optional[float], d: int = 2) -> Optional[float]:
    if x is None:
        return None
    return round(float(x), d)


def historical_cagrs(annual: list[dict[str, Any]]) -> dict[str, Optional[float]]:
    if len(annual) < MIN_ANNUAL_OBS:
        return {k: None for k in ("revenue", "pat", "eps", "ebitda", "equity", "fcf")}
    return {
        "revenue": cagr(series_field(annual, "revenue", "total_revenue", "sales")),
        "pat": cagr(series_field(annual, "pat", "net_income", "profit_after_tax")),
        "eps": cagr(series_field(annual, "eps")),
        "ebitda": cagr(series_field(annual, "ebitda")),
        "equity": cagr(series_field(annual, "equity", "shareholders_equity")),
        "fcf": cagr(series_field(annual, "free_cash_flow", "fcf")),
    }


def latest_margins(annual: list[dict[str, Any]]) -> dict[str, Optional[float]]:
    if not annual:
        return {}
    last = annual[-1]
    rev = metric(last, "revenue", "total_revenue", "sales")
    if not rev or rev == 0:
        return {}
    ebitda = metric(last, "ebitda")
    ebit = metric(last, "ebit", "operating_profit")
    pat = metric(last, "pat", "net_income")
    gp = metric(last, "gross_profit")
    return {
        "gross_margin": (gp / rev) if gp is not None else None,
        "ebitda_margin": (ebitda / rev) if ebitda is not None else None,
        "operating_margin": (ebit / rev) if ebit is not None else None,
        "net_margin": (pat / rev) if pat is not None else None,
    }


def _horizon_years(window: str) -> float:
    return {
        "NQ": 0.25,
        "FY+1": 1.0,
        "FY+2": 2.0,
        "FY+3": 3.0,
        "FY+5": 5.0,
    }.get(window, 1.0)


def project_line(
    base: Optional[float],
    growth: Optional[float],
    *,
    scenario: str = "base",
) -> dict[str, Optional[float]]:
    """Project a level across forecast windows under one scenario."""
    if base is None or base <= 0 or growth is None:
        return {w: None for w in WINDOWS}
    g = growth * SCENARIO_GROWTH_MULT.get(scenario, 1.0)
    out: dict[str, Optional[float]] = {}
    for w in WINDOWS:
        years = _horizon_years(w)
        out[w] = _round(base * ((1.0 + g) ** years))
    return out


def business_forecast(annual: list[dict[str, Any]], *, scenario: str = "base") -> dict[str, Any]:
    if len(annual) < MIN_ANNUAL_OBS:
        return {"ok": False, "error": "insufficient_history", "lines": {}}
    last = annual[-1]
    cagrs = historical_cagrs(annual)
    rev_g = cagrs.get("revenue")
    # Fallback growth to 0 when only levels exist but CAGR unavailable — still mark assumed.
    if rev_g is None:
        rev_g = 0.0
    lines = {
        "revenue": project_line(metric(last, "revenue", "total_revenue", "sales"), rev_g, scenario=scenario),
        "ebitda": project_line(metric(last, "ebitda"), cagrs.get("ebitda") if cagrs.get("ebitda") is not None else rev_g, scenario=scenario),
        "ebit": project_line(metric(last, "ebit", "operating_profit"), cagrs.get("ebitda") if cagrs.get("ebitda") is not None else rev_g, scenario=scenario),
        "pat": project_line(metric(last, "pat", "net_income"), cagrs.get("pat") if cagrs.get("pat") is not None else rev_g, scenario=scenario),
        "eps": project_line(metric(last, "eps"), cagrs.get("eps") if cagrs.get("eps") is not None else rev_g, scenario=scenario),
        "book_value": project_line(metric(last, "equity", "shareholders_equity"), cagrs.get("equity") if cagrs.get("equity") is not None else rev_g * 0.8, scenario=scenario),
        "operating_cash_flow": project_line(metric(last, "cfo", "operating_cash_flow"), rev_g, scenario=scenario),
        "free_cash_flow": project_line(metric(last, "free_cash_flow", "fcf"), cagrs.get("fcf") if cagrs.get("fcf") is not None else rev_g, scenario=scenario),
    }
    base_values = {
        "revenue": metric(last, "revenue", "total_revenue", "sales"),
        "ebitda": metric(last, "ebitda"),
        "ebit": metric(last, "ebit", "operating_profit"),
        "pat": metric(last, "pat", "net_income"),
        "eps": metric(last, "eps"),
        "book_value": metric(last, "equity", "shareholders_equity"),
        "operating_cash_flow": metric(last, "cfo", "operating_cash_flow"),
        "free_cash_flow": metric(last, "free_cash_flow", "fcf"),
    }
    return {
        "ok": True,
        "scenario": scenario,
        "base_period": last.get("fiscal_year") or last.get("period"),
        "growth_rates_used": {k: _pct(v) for k, v in cagrs.items()},
        "base_values": base_values,
        "lines": lines,
    }


def profitability_forecast(annual: list[dict[str, Any]], *, scenario: str = "base") -> dict[str, Any]:
    margins = latest_margins(annual)
    if not margins:
        return {"ok": False, "error": "no_margins", "margins": {}}
    delta = SCENARIO_MARGIN_DELTA_PP.get(scenario, 0.0) / 100.0
    out = {}
    for k, v in margins.items():
        if v is None:
            out[k] = {w: None for w in WINDOWS}
            continue
        adj = max(-0.5, min(0.8, v + delta))
        out[k] = {w: _pct(adj) for w in WINDOWS}
    # ROE / ROCE / ROA from latest statement if present
    last = annual[-1] if annual else {}
    for name, keys in (
        ("roe", ("roe",)),
        ("roce", ("roce",)),
        ("roa", ("roa",)),
    ):
        base = metric(last, *keys)
        if base is None:
            # derive rough ROE = PAT/equity
            if name == "roe":
                pat = metric(last, "pat", "net_income")
                eq = metric(last, "equity", "shareholders_equity")
                if pat is not None and eq and eq > 0:
                    base = 100.0 * pat / eq
        out[name] = {w: _round(base + (SCENARIO_MARGIN_DELTA_PP.get(scenario, 0.0) * 0.5), 2) if base is not None else None for w in WINDOWS}
    return {"ok": True, "scenario": scenario, "margins": out}


def balance_sheet_forecast(annual: list[dict[str, Any]], *, scenario: str = "base") -> dict[str, Any]:
    if not annual:
        return {"ok": False, "error": "no_statements", "lines": {}}
    last = annual[-1]
    cagrs = historical_cagrs(annual)
    g = cagrs.get("equity") if cagrs.get("equity") is not None else cagrs.get("revenue") or 0.0
    cash = metric(last, "cash")
    debt = metric(last, "debt", "total_debt")
    equity = metric(last, "equity", "shareholders_equity")
    wc = metric(last, "working_capital")
    lines = {
        "cash": project_line(cash, g, scenario=scenario),
        "debt": project_line(debt, g * 0.5, scenario=scenario),
        "book_value": project_line(equity, g, scenario=scenario),
        "working_capital": project_line(wc, g, scenario=scenario),
        "capital_employed": project_line(
            (equity + (debt or 0.0)) if equity is not None else None,
            g,
            scenario=scenario,
        ),
    }
    net_debt = {}
    for w in WINDOWS:
        c = lines["cash"].get(w)
        d = lines["debt"].get(w)
        net_debt[w] = _round(d - c) if c is not None and d is not None else None
    lines["net_debt"] = net_debt
    leverage = {}
    for w in WINDOWS:
        d = lines["debt"].get(w)
        e = lines["book_value"].get(w)
        leverage[w] = _round(d / e, 3) if d is not None and e and e > 0 else None
    lines["leverage"] = leverage
    return {"ok": True, "scenario": scenario, "lines": lines}


def scenario_probabilities(*, stability: float, confidence_score: float) -> dict[str, float]:
    """Assign bull/base/bear that always sum to 100."""
    # Higher stability → more base weight; lower confidence → more bear.
    stab = max(0.0, min(1.0, stability))
    conf = max(0.0, min(1.0, confidence_score))
    base = 45.0 + 25.0 * stab
    bull = 20.0 + 15.0 * conf * (1.0 - 0.3 * (1.0 - stab))
    bear = 100.0 - base - bull
    if bear < 10.0:
        shift = 10.0 - bear
        bear = 10.0
        base = max(30.0, base - shift)
        bull = 100.0 - base - bear
    # Normalize rounding
    vals = {"bull": round(bull, 1), "base": round(base, 1), "bear": round(bear, 1)}
    drift = round(100.0 - sum(vals.values()), 1)
    vals["base"] = round(vals["base"] + drift, 1)
    return vals
