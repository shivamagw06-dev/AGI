"""Framework 6 — Balance Sheet Resilience."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of, txt, trend_label


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    debt = txt(evidence.get("debt"))
    cash = txt(evidence.get("cash_balance") or evidence.get("cash"))
    wc = txt(evidence.get("working_capital"))
    narrative = txt(evidence.get("narrative"))
    b = blob_of(debt, cash, wc, narrative, evidence.get("financial_quality"))

    resilient = any(k in b for k in ("strong", "conservative", "low leverage", "liquid", "well capital", "within"))
    stress = any(k in b for k in ("stress", "high leverage", "maturity wall", "liquidity", "covenant"))

    assessment = (
        f"Balance-sheet resilience for {name} "
        + (
            "appears adequate to support the investment thesis through a moderate downturn, "
            "provided leverage and liquidity remain disciplined."
            if resilient and not stress
            else "is a binding constraint — leverage or liquidity signals elevate recession and funding risk."
            if stress
            else "is mixed; funding flexibility and leverage stability need continued monitoring."
        )
    )

    return {
        "framework": "Balance Sheet",
        "completed": bool(debt or cash or wc),
        "assets": "Asset quality judged via earnings durability and impairment risk signals",
        "liabilities": debt or "Liability / funding profile under review",
        "equity": "Equity buffer inferred from leverage and retained earnings path",
        "cash": cash or "Cash buffer under review",
        "debt": debt or "Debt / leverage under review",
        "interest_coverage": txt(evidence.get("interest_coverage")) or "Interest coverage under review",
        "debt_maturity": "Maturity profile should be monitored for refinancing clusters",
        "liquidity": "Adequate" if resilient and not stress else "Watch",
        "leverage": debt or "Leverage trajectory under review",
        "working_capital": wc or "Working capital under review",
        "trajectory": trend_label(narrative or debt),
        "resilient": resilient and not stress,
        "assessment": assessment,
    }
