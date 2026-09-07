"""Framework 2 — Returns Assessment (ROE / ROIC / economic profit)."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import blob_of, parse_num, txt, trend_label


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    roe = txt(evidence.get("roe"))
    roic = txt(evidence.get("roic"))
    trend = txt(evidence.get("trend"))
    narrative = txt(evidence.get("narrative"))
    b = blob_of(roe, roic, trend, narrative, evidence.get("capital_allocation"))

    roe_n = parse_num(roe)
    roic_n = parse_num(roic)
    attractive = (roe_n is not None and roe_n >= 15) or (roic_n is not None and roic_n >= 12) or any(
        k in b for k in ("high return", "strong return", "above cost", "economic profit")
    )
    leverage_driven = "leverage" in b and "stable" not in b

    assessment = (
        f"Returns on capital for {name} appear attractive"
        + (
            ", and the improvement is more consistent with stronger profitability than with added leverage"
            if attractive and not leverage_driven
            else ", but leverage contribution versus operating improvement still needs separation"
            if attractive
            else " remain only adequate on present evidence"
        )
        + ". Persistence depends on incremental returns on new capital remaining above opportunity cost."
    )

    return {
        "framework": "Returns",
        "completed": bool(roe or roic or "return" in b),
        "roe": roe or "n/a",
        "roa": txt(evidence.get("roa")) or "n/a",
        "roic": roic or "n/a",
        "croic": txt(evidence.get("croic")) or "Cash return on capital under review",
        "incremental_roic": (
            "Incremental ROIC likely supportive if growth is self-funded and margins hold"
            if attractive
            else "Incremental ROIC not yet confirmed as value-accretive"
        ),
        "economic_profit": (
            "Economic profit plausible where returns clear the cost of capital"
            if attractive
            else "Economic profit not clearly evidenced"
        ),
        "eva": "EVA lens: value created only when ROIC exceeds cost of capital on a sustained basis",
        "trajectory": trend_label(trend or narrative, score=roe_n),
        "attractive": attractive,
        "assessment": assessment,
    }
