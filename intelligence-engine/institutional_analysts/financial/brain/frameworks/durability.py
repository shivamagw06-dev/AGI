"""Framework 8 — Financial Durability / recession resilience."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of, txt


def assess(evidence: dict[str, Any], pieces: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    bs = pieces.get("balance_sheet") or {}
    cash = pieces.get("cash_flow") or {}
    returns = pieces.get("returns") or {}
    profit = pieces.get("profitability") or {}
    b = blob_of(
        bs.get("assessment"),
        cash.get("assessment"),
        returns.get("assessment"),
        profit.get("trajectory"),
        evidence.get("financial_quality"),
    )

    resilient = bool(bs.get("resilient")) and cash.get("cash_conversion") != "Watch"
    stable_margins = str(profit.get("trajectory") or "") in {"Improving", "Stable"}
    stable_returns = bool(returns.get("attractive"))

    assessment = (
        f"{name} could withstand a moderate recession with relatively limited thesis damage"
        if resilient and stable_margins
        else f"{name}'s financial durability is not yet institutional-grade for a severe downturn"
        if not resilient
        else f"{name} shows mixed recession resilience — cash and leverage need to stay disciplined"
    )

    return {
        "framework": "Financial Durability",
        "completed": True,
        "resilience": "Higher" if resilient else "Mixed",
        "cash_buffer": bs.get("liquidity") or "Watch",
        "funding": bs.get("debt") or "Funding flexibility under review",
        "margin_stability": "Stable/Improving" if stable_margins else "Less stable",
        "return_stability": "Supported" if stable_returns else "Uncertain",
        "leverage_stability": "Acceptable" if resilient else "Elevated watch",
        "recession_ready": bool(resilient and stable_margins),
        "assessment": assessment,
        "signals": b[:180],
    }
