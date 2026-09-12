"""Consensus engine — street / guidance / AGIB / committee / portfolio disagreements."""

from __future__ import annotations

from typing import Any


def consensus_compare(
    profile: dict[str, Any],
    *,
    probabilities: dict[str, Any] | None = None,
    portfolio_soft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    market = (profile.get("market_expects") or {}).get("narrative") or "Street consensus unavailable"
    guidance = "Management guidance monitored via FIL/FDI soft layers (not redesigned here)"
    agib = (profile.get("agib_base") or {}).get("narrative") or "AGIB base scenario narrative"
    most = (probabilities or {}).get("most_likely")
    committee = f"Committee should debate probability mass on {most or 'base'} vs tails — not price targets"
    pio = "Portfolio Office receives scenario impact / stress exposure (suitability only)"
    if portfolio_soft:
        pio = (
            f"Portfolio soft context: grade {portfolio_soft.get('health_grade')} · "
            f"net effect {((portfolio_soft.get('impact') or {}).get('net_portfolio_effect'))}"
        )
    disagreements = []
    if most and most != "base":
        disagreements.append(
            {
                "parties": ["street_implied_base", "agib_most_likely"],
                "topic": "scenario_skew",
                "detail": f"AGIB most-likely is {most}, while street narrative is base-leaning",
            }
        )
    market_loan = (profile.get("market_expects") or {}).get("loan_growth_pct")
    agib_loan = (profile.get("agib_base") or {}).get("loan_growth_pct")
    if isinstance(market_loan, (int, float)) and isinstance(agib_loan, (int, float)) and market_loan != agib_loan:
        disagreements.append(
            {
                "parties": ["street", "agib"],
                "topic": "loan_growth",
                "detail": f"Street {market_loan}% vs AGIB {agib_loan}%",
            }
        )
    return {
        "street_consensus": market,
        "management_guidance": guidance,
        "agib_analysts": agib,
        "investment_committee": committee,
        "portfolio_office": pio,
        "disagreements": disagreements,
        "rule": "Highlight disagreements — committee debates scenario probabilities, not price targets",
    }
