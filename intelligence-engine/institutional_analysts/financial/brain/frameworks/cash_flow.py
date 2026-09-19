"""Framework 5 — Cash Flow."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of, txt, trend_label


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    cash = txt(evidence.get("cash_flow"))
    wc = txt(evidence.get("working_capital"))
    trend = txt(evidence.get("trend"))
    narrative = txt(evidence.get("narrative"))
    b = blob_of(cash, wc, trend, narrative)

    converting = any(k in b for k in ("cash conversion", "operating cash", "fcf", "free cash", "improv"))
    weak = any(k in b for k in ("mismatch", "weak cash", "working capital drag", "cash burn"))

    assessment = (
        f"Cash generation for {name} "
        + (
            "is improving relative to accounting profit, suggesting growth and earnings are supported by "
            "underlying cash fundamentals rather than working-capital or recognition distortions."
            if converting and not weak
            else "shows conversion gaps that weaken confidence in reported profit quality until operating cash "
            "and free cash flow confirm the earnings path."
            if weak
            else "requires continued confirmation that accounting profit converts cleanly into free cash flow."
        )
    )

    return {
        "framework": "Cash Flow",
        "completed": bool(cash or wc or "cash" in b),
        "operating_cash_flow": cash or "Operating cash flow under review",
        "free_cash_flow": cash or "Free cash flow under review",
        "cash_conversion": "Improving" if converting and not weak else "Watch" if weak else "Mixed",
        "cash_conversion_cycle": wc or "Cash conversion cycle / working-capital cycle under review",
        "working_capital": wc or "Working capital intensity under review",
        "capex": txt(evidence.get("capex")) or "Capex split (maintenance vs growth) under review",
        "maintenance_capex": "Maintenance capex inferred within reinvestment needs",
        "growth_capex": "Growth capex justified only when incremental returns remain attractive",
        "trajectory": trend_label(trend or narrative),
        "assessment": assessment,
    }
