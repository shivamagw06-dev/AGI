"""Risk producers — beta, vol, VaR, ES, drawdown, liquidity (from KF / fundamentals)."""

from __future__ import annotations

from typing import Any


def produce_risk(entity: str) -> dict[str, Any]:
    e = entity.upper()
    try:
        from institutional_reasoning.fundamentals.risk_derivations import derive_risk_metrics

        risk = derive_risk_metrics(e)
    except Exception:
        risk = None
    if not risk:
        return {"found": False, "entity": e, "insufficient": True, "reason": "no_return_series"}
    drivers = risk.get("risk_drivers") or {}
    downside = risk.get("downside") or {}
    return {
        "found": True,
        "entity": e,
        "beta": drivers.get("beta_vs_benchmark"),
        "volatility_ann_pct": drivers.get("volatility_ann_pct"),
        "correlation": drivers.get("correlation_vs_benchmark"),
        "var_95_monthly_pct": downside.get("var_95_monthly_pct"),
        "expected_shortfall_95_pct": downside.get("expected_shortfall_95_pct"),
        "max_drawdown_pct": downside.get("max_drawdown_pct"),
        "liquidity_score": drivers.get("liquidity_score"),
        "factor_exposure": drivers.get("factor_exposure"),
        "formulas": risk.get("formulas"),
        "provider": "kf_risk_producer",
        "derived_not_stored": True,
    }
