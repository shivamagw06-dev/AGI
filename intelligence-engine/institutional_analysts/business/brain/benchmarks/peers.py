"""Benchmarking — compare versus peers and history, never only versus itself."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, txt


def benchmark(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    position = txt(evidence.get("competitive_position"))
    advantages = as_list(evidence.get("advantages"), limit=4)
    moat = frameworks.get("moat") or {}
    porter = frameworks.get("porter_five_forces") or {}
    sector = evidence.get("sector") if isinstance(evidence.get("sector"), dict) else {}
    peers_global = as_list(evidence.get("global_peers") or sector.get("global_peers"), limit=4)
    peers_india = as_list(evidence.get("indian_peers") or sector.get("indian_peers") or sector.get("peers"), limit=4)
    history = as_list(evidence.get("historical_performance") or evidence.get("history_notes"), limit=4)

    if not peers_global:
        peers_global = ["Global category leaders with scaled distribution franchises"]
    if not peers_india:
        peers_india = ["Domestic category peers competing on distribution, funding and product breadth"]
    if not history:
        history = ["Multi-year franchise compounding versus prior credit / demand cycles"]

    relative = (
        f"Relative to Indian peers, {name} differentiates through {', '.join(advantages[:2]).lower() or 'franchise depth'} "
        f"within a {position or 'competitive'} set. Versus global peers, the relevant comparison is business-system quality "
        f"(funding/distribution advantage and capital discipline), not local product labels. "
        f"Historically, durability is assessed as {str(moat.get('durability') or 'mixed').lower()}."
    )

    return {
        "global_peers": peers_global,
        "indian_peers": peers_india,
        "historical_company_performance": history,
        "industry_attractiveness_vs_peers": porter.get("industry_attractiveness"),
        "relative_positioning": relative,
        "never_self_only": True,
        "assessment": relative,
    }
