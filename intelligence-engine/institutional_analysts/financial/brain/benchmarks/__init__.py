"""Financial benchmarking — peers and history, never self-only."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import as_list, txt


def benchmark(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    sector = evidence.get("sector") if isinstance(evidence.get("sector"), dict) else {}
    indian = as_list(evidence.get("indian_peers") or sector.get("indian_peers") or sector.get("peers"), limit=4)
    global_p = as_list(evidence.get("global_peers") or sector.get("global_peers"), limit=4)
    history = as_list(evidence.get("history_notes"), limit=4)
    if not indian:
        indian = ["Domestic sector peers on margins, returns and leverage"]
    if not global_p:
        global_p = ["Global category peers on cash conversion and ROIC"]
    if not history:
        history = ["Own multi-year margin / return / cash path"]

    rets = frameworks.get("returns") or {}
    cash = frameworks.get("cash_flow") or {}
    relative = (
        f"Versus Indian peers, {name} should be judged on return on capital, cash conversion and leverage "
        f"discipline — currently returns look {'attractive' if rets.get('attractive') else 'only adequate'} "
        f"and cash conversion is {str(cash.get('cash_conversion') or 'mixed').lower()}. "
        f"Versus global peers, the benchmark is persistence of ROIC and free-cash-flow conversion, "
        f"not a single-period print. Historical self-comparison is necessary but insufficient alone."
    )
    return {
        "indian_peers": indian,
        "global_peers": global_p,
        "historical_company_performance": history,
        "sector_averages": txt(sector.get("structure") or sector.get("priority_metrics"))
        or "Sector average returns / margins used as qualitative context",
        "never_self_only": True,
        "assessment": relative,
    }
