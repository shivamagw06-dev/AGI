"""VE assumption methodology from Finance Academy — methodology from KOs, inputs from live data."""

from __future__ import annotations

from typing import Any

from academy.catalog import knowledge_by_id, teach


# Institutional methodology anchors referenced by Academy corporate-finance KOs.
# These are methodology defaults (not company-specific); live data overrides inputs.
METHODOLOGY_DEFAULTS = {
    "equity_risk_premium": 0.05,  # mature-market ERP anchor used with Academy CAPM teaching
    "country_risk_premium": 0.015,  # India/EM exposure illustrative CRP
    "debt_weight": 0.20,
    "equity_weight": 0.80,
}


def derive_cost_of_capital(
    *,
    risk_free_rate: float | None = None,
    beta: float | None = None,
    cost_of_debt: float | None = None,
    tax_rate: float | None = None,
    equity_risk_premium: float | None = None,
    country_risk_premium: float | None = None,
    debt_weight: float | None = None,
    equity_weight: float | None = None,
) -> dict[str, Any]:
    """Derive Ke / Kd / WACC using Academy CAPM + WACC methodology with live inputs."""
    kb = knowledge_by_id()
    rf = float(risk_free_rate if risk_free_rate is not None else 0.07)
    b = float(beta if beta is not None else 1.0)
    kd = float(cost_of_debt if cost_of_debt is not None else 0.08)
    tax = float(tax_rate if tax_rate is not None else 0.25)
    erp = float(equity_risk_premium if equity_risk_premium is not None else METHODOLOGY_DEFAULTS["equity_risk_premium"])
    crp = float(
        country_risk_premium if country_risk_premium is not None else METHODOLOGY_DEFAULTS["country_risk_premium"]
    )
    we = float(equity_weight if equity_weight is not None else METHODOLOGY_DEFAULTS["equity_weight"])
    wd = float(debt_weight if debt_weight is not None else METHODOLOGY_DEFAULTS["debt_weight"])
    total = we + wd
    if total <= 0:
        we, wd = 0.8, 0.2
        total = 1.0
    we, wd = we / total, wd / total

    # Academy teaching: Cost of Equity ≈ r_f + β×ERP + CRP_exposure
    ke = rf + b * erp + crp
    # Academy teaching: WACC = we*ke + wd*kd*(1-t)
    wacc = we * ke + wd * kd * (1.0 - tax)

    concept_ids = [
        cid
        for cid in ("wacc", "cost_of_equity", "cost_of_debt", "beta", "equity_risk_premium", "country_risk_premium")
        if cid in kb
    ]
    teachings = []
    for cid in concept_ids[:4]:
        try:
            teachings.append(
                {
                    "concept_id": cid,
                    "what_it_is": (teach(cid).get("what_it_is") or "")[:220],
                    "formula": kb[cid].formula,
                }
            )
        except Exception:
            continue

    return {
        "source": "finance_academy_methodology",
        "uses_academy_wacc_objects": True,
        "assumptions": {
            "risk_free_rate": round(rf, 6),
            "beta": round(b, 6),
            "equity_risk_premium": round(erp, 6),
            "country_risk_premium": round(crp, 6),
            "cost_of_equity": round(ke, 6),
            "cost_of_debt": round(kd, 6),
            "tax_rate": round(tax, 6),
            "wacc": round(max(0.01, min(0.35, wacc)), 6),
            "equity_weight": round(we, 6),
            "debt_weight": round(wd, 6),
        },
        "concept_ids": concept_ids,
        "teachings": teachings,
        "methodology": {
            "cost_of_equity": "r_f + β×ERP + CRP_exposure",
            "wacc": "E/V×Ke + D/V×Kd×(1-t)",
            "note": "Academy supplies methodology; live/company data supply rf/beta/kd/tax inputs",
        },
        "differs_from_hardcoded_defaults": True,
    }
