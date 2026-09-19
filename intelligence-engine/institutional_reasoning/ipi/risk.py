"""Module 3 — Risk Intelligence.

Evidence-backed risk metrics for every supported portfolio recommendation.
Prefers derived producers (VaR, ES, beta, correlation, liquidity) from
primitive return series when available; falls back to book seed proxies.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ipi.portfolio_book import default_book, holding_for

RISK_VERSION = "risk-intelligence-v1.1.0"


def _f(v: Any, default: float | None = None) -> float | None:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _derived_risk(symbol: str) -> dict[str, Any] | None:
    try:
        from institutional_reasoning.fundamentals.risk_derivations import derive_risk_metrics

        return derive_risk_metrics(symbol)
    except Exception:
        return None


def compute_risk(
    *,
    entity_id: str | None,
    book: dict[str, Any] | None = None,
    candidate_weight: float | None = None,
    downside: dict[str, Any] | None = None,
) -> dict[str, Any]:
    book = book or default_book()
    symbol = str(entity_id or "").upper()
    holding = holding_for(symbol, book) or {}
    derived = _derived_risk(symbol) if symbol else None
    drivers_detail = (derived or {}).get("risk_drivers") or {}
    downside_detail = (derived or {}).get("downside") or {}

    # Prefer derived annualised vol / beta; else book seeds.
    vol = _f(drivers_detail.get("volatility_ann_pct"))
    if vol is not None:
        vol = vol / 100.0  # series stored as percent
    else:
        vol = _f(holding.get("volatility"), 0.24) or 0.24
    beta = _f(drivers_detail.get("beta_vs_benchmark"))
    if beta is None:
        beta = _f(holding.get("beta"), 1.0) or 1.0
    corr = _f(drivers_detail.get("correlation_vs_benchmark"))
    weight = _f(candidate_weight)
    if weight is None:
        weight = _f(holding.get("weight"), 0.0) or 0.0

    # Portfolio vol proxy = weighted sum of vols (no full cov matrix — non-goal).
    holdings = book.get("holdings") or []
    port_vol = 0.0
    port_w = 0.0
    for h in holdings:
        w = _f(h.get("weight"), 0.0) or 0.0
        v = _f(h.get("volatility"), 0.22) or 0.22
        # Prefer derived vol for known holdings when present
        d = _derived_risk(str(h.get("symbol") or ""))
        if d:
            dv = _f((d.get("risk_drivers") or {}).get("volatility_ann_pct"))
            if dv is not None:
                v = dv / 100.0
        port_vol += w * v
        port_w += w
    port_vol = port_vol / port_w if port_w else 0.22

    # Marginal risk contribution ≈ weight * vol / portfolio_vol
    risk_contribution = round((weight * vol) / max(port_vol, 1e-6), 4) if weight > 0 else 0.0
    # Correlation bump if another same-sector name already large
    sector = str(holding.get("sector") or "")
    peer_w = sum(
        _f(h.get("weight"), 0.0) or 0.0
        for h in holdings
        if str(h.get("sector") or "") == sector and str(h.get("symbol") or "").upper() != symbol
    )
    if peer_w >= 0.15:
        risk_contribution = round(risk_contribution * (1.0 + min(0.5, peer_w)), 4)

    # Position-scaled VaR / ES from historical simulation when derived; else parametric.
    if downside_detail.get("var_95_monthly_pct") is not None:
        var_95 = round(abs(float(downside_detail["var_95_monthly_pct"])) / 100.0 * max(weight, 0.01), 4)
        es_95 = round(
            abs(float(downside_detail.get("expected_shortfall_95_pct") or downside_detail["var_95_monthly_pct"]))
            / 100.0
            * max(weight, 0.01),
            4,
        )
        max_dd = round(min(0.55, abs(float(downside_detail.get("max_drawdown_pct") or 0.0)) / 100.0), 4)
        producer = "derived_risk_producer"
    else:
        var_95 = round(1.65 * vol * max(weight, 0.01), 4)
        es_95 = round(2.06 * vol * max(weight, 0.01), 4)
        max_dd = round(min(0.55, vol * 2.2), 4)
        producer = "book_proxy"

    tail = round(abs(_f((downside or {}).get("worst_case"), vol * 1.8) or vol * 1.8), 4)
    liq = _f(drivers_detail.get("liquidity_score"))
    if liq is None:
        liq = _f(holding.get("liquidity_score"), 0.8) or 0.8
    liquidity_risk = round(max(0.0, 1.0 - liq), 4)
    concentration_risk = round(max(weight, peer_w), 4)

    policy = book.get("policy") or {}
    risk_budget = _f(policy.get("risk_budget"), 0.12) or 0.12

    drivers = []
    if risk_contribution > (_f(policy.get("max_single_name_risk_contribution"), 0.18) or 0.18):
        drivers.append("single_name_risk_budget")
    if peer_w >= 0.15:
        drivers.append("sector_correlation")
    if corr is not None and corr >= 0.75 and peer_w >= 0.10:
        drivers.append("high_benchmark_correlation")
    if liquidity_risk >= 0.45:
        drivers.append("liquidity")
    if _f(drivers_detail.get("idiosyncratic_vol_pct"), 0) and float(
        drivers_detail.get("idiosyncratic_vol_pct") or 0
    ) >= 15.0:
        drivers.append("idiosyncratic_volatility")
    if not drivers:
        drivers = ["market_beta", "volatility"]

    return {
        "found": True,
        "risk_version": RISK_VERSION,
        "entity_id": symbol or None,
        "volatility": round(vol, 4),
        "beta": round(beta, 4),
        "correlation": round(corr, 4) if corr is not None else None,
        "var": var_95,
        "expected_shortfall": es_95,
        "maximum_drawdown": max_dd,
        "risk_contribution": risk_contribution,
        "risk_share": risk_contribution,
        "var_contribution": risk_contribution,
        "tail_risk": tail,
        "liquidity_risk": liquidity_risk,
        "concentration_risk": concentration_risk,
        "sector_risk": round(peer_w + weight, 4),
        "country_risk": 0.05 if str(holding.get("country") or "IN") == "IN" else 0.15,
        "currency_risk": 0.04 if str(holding.get("currency") or "INR") == "INR" else 0.12,
        "risk_budget": risk_budget,
        "risk_budget_used": round(min(1.0, risk_contribution / max(risk_budget, 1e-6)), 4),
        "risk_drivers": drivers,
        "factor_exposure": drivers_detail.get("factor_exposure"),
        "derived_metrics": {
            "risk_drivers": drivers_detail or None,
            "downside": downside_detail or None,
            "formulas": (derived or {}).get("formulas"),
            "provider": producer,
        }
        if derived
        else {"provider": producer},
        "portfolio_volatility_proxy": round(port_vol, 4),
        "provider": producer,
    }
