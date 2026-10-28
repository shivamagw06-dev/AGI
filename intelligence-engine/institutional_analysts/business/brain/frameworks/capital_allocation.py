"""Framework 9 — Capital Allocation."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    capital = txt(evidence.get("capital_allocation"))
    growth = as_list(evidence.get("growth_opportunities"), limit=4)
    score = evidence.get("business_quality_score")
    b = blob_of(capital, growth, evidence.get("business_model"))

    reinvestment = (
        "Reinvestment into the core franchise appears prioritised"
        if any(k in b for k in ("reinvest", "franchise", "capacity", "distribution", "growth"))
        else "Reinvestment posture needs clearer evidence"
    )
    acquisitions = (
        "Acquisition activity must be judged by incremental return on capital, not deal volume"
    )
    buybacks = "Buybacks / owner returns are value-accretive only when priced below intrinsic business worth — assessed elsewhere."
    dividends = "Dividends are a residual after high-return reinvestment opportunities are funded."
    debt = (
        "Balance-sheet / leverage discipline is part of franchise resilience"
        if any(k in b for k in ("conservative", "disciplin", "capital", "debt"))
        else "Leverage policy requires monitoring through stress periods"
    )
    roic_view = (
        "Historical franchise quality suggests returns on capital have been adequate to superior"
        if score is not None and float(score) >= 65
        else "Return on incremental capital is the binding test for growth ambition"
    )

    assessment = (
        f"{name}'s capital allocation creates long-term value when incremental capital earns above "
        f"opportunity cost — currently evidenced by {capital.lower().rstrip('.') if capital else 'franchise reinvestment posture'}."
    )

    return {
        "framework": "Capital Allocation",
        "completed": bool(capital),
        "reinvestment": reinvestment,
        "acquisitions": acquisitions,
        "buybacks": buybacks,
        "dividends": dividends,
        "debt": debt,
        "roic": roic_view,
        "return_on_incremental_capital": roic_view,
        "assessment": assessment,
        "what_creates_long_term_returns": assessment,
    }
