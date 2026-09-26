"""Framework 7 — Capital Allocation."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    capital = txt(evidence.get("capital_allocation"))
    roic = txt(evidence.get("roic"))
    cash = txt(evidence.get("cash_flow"))
    b = blob_of(capital, roic, cash, evidence.get("trend"))

    disciplined = any(k in b for k in ("disciplin", "conservative", "efficient", "buyback", "dividend", "debt reduction", "reinvest"))
    value_creating = disciplined or any(k in b for k in ("roic", "return", "shareholder"))

    assessment = (
        f"Capital allocation at {name} "
        + (
            "appears oriented toward shareholder value when reinvestment, distributions and balance-sheet "
            "choices are judged against return on incremental capital rather than growth for its own sake."
            if value_creating
            else "does not yet clearly demonstrate that deployed capital earns above its opportunity cost."
        )
    )

    return {
        "framework": "Capital Allocation",
        "completed": bool(capital),
        "reinvestment": "Reinvestment prioritized where incremental returns remain attractive" if "reinvest" in b or capital else "Reinvestment posture under review",
        "acquisitions": "Acquisitions judged by post-deal returns, not deal volume",
        "dividends": "Dividends are a residual after high-return reinvestment",
        "share_buybacks": "Buybacks create value only below intrinsic business worth — assessed elsewhere",
        "debt_reduction": "Debt reduction supportive when leverage was a constraint",
        "capital_efficiency": capital or "Capital efficiency under review",
        "roic_vs_cost_of_capital": (
            "Returns appear to clear opportunity cost on present signals"
            if roic or "return" in b
            else "ROIC versus cost of capital still qualitative"
        ),
        "shareholder_value_created": bool(value_creating),
        "assessment": assessment,
    }
