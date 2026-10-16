"""Natural transitions between institutional report sections."""

from __future__ import annotations

TRANSITIONS = {
    ("business_intelligence", "financial_intelligence"): (
        "The strength of the business model is ultimately reflected in its financial performance."
    ),
    ("financial_intelligence", "valuation_intelligence"): (
        "The next question is whether these operating fundamentals are already reflected in today's valuation."
    ),
    ("valuation_intelligence", "market_intelligence"): (
        "Although intrinsic value remains the primary consideration, current market positioning "
        "provides useful context for investor expectations."
    ),
    ("market_intelligence", "sector_intelligence"): (
        "Market behaviour should be read against the industry structure that shapes durable returns."
    ),
    ("sector_intelligence", "macro_intelligence"): (
        "Industry dynamics sit within a broader macro regime that transmits through funding costs, "
        "demand and risk appetite."
    ),
    ("macro_intelligence", "risks"): (
        "With the external backdrop framed, attention turns to what can impair the investment case."
    ),
    ("risks", "scenarios"): (
        "These risk channels inform the probability-weighted bull, base and bear paths."
    ),
    ("scenarios", "conclusion"): (
        "Taken together, the scenarios and risk register support a single institutional conclusion."
    ),
    ("management", "ownership"): (
        "Governance quality should be read alongside who owns the equity and how that ownership is evolving."
    ),
    ("ownership", "risks"): (
        "Ownership and alignment signals feed directly into the residual risk assessment."
    ),
}


def transition_for(prev: str, nxt: str) -> str | None:
    return TRANSITIONS.get((prev, nxt))


def with_transitions(sections: dict[str, str], order: list[str]) -> dict[str, str]:
    """Attach lead-in transitions without inventing facts."""
    out = dict(sections)
    for i in range(1, len(order)):
        prev, nxt = order[i - 1], order[i]
        if not out.get(nxt):
            continue
        lead = transition_for(prev, nxt)
        if lead and not out[nxt].startswith(lead[:40]):
            out[nxt] = f"{lead} {out[nxt]}"
    return out
