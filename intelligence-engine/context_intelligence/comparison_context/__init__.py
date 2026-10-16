"""Decide which comparison lenses are required."""

from __future__ import annotations

import re
from typing import Any


def detect_comparison_context(
    question: str,
    *,
    primary_objective: str | None = None,
    peers: list[str] | None = None,
    entity: str | None = None,
) -> dict[str, Any]:
    text = question or ""
    lenses: list[str] = []
    if re.search(r"\b(versus\s+history|vs\s+history|historical)\b", text, re.I) or primary_objective == "Historical Analysis":
        lenses.append("History")
    if re.search(r"\b(compare|vs\.?|versus|peer)\b", text, re.I) or primary_objective == "Peer Comparison":
        lenses.append("Peers")
    if primary_objective in {"Investment Evaluation", "Valuation Assessment", "Sector Attractiveness"}:
        for x in ("Peers", "History"):
            if x not in lenses:
                lenses.append(x)
    if primary_objective in {"Sector Attractiveness", "Macro Impact"}:
        if "Sector" not in lenses:
            lenses.append("Sector")
    if primary_objective == "Portfolio Decision":
        lenses.append("Portfolio")
    if re.search(r"\b(global|worldwide|vs\s+us)\b", text, re.I):
        lenses.append("Global")
    if re.search(r"\b(market|nifty\s*50|sensex)\b", text, re.I) and "Market" not in lenses:
        if primary_objective in {"Historical Analysis", "Sector Attractiveness"}:
            lenses.append("Market")

    # Deduplicate preserve order
    seen = set()
    ordered = []
    for x in lenses:
        if x not in seen:
            seen.add(x)
            ordered.append(x)

    peer_names = list(peers or [])
    relevant: list[str] = []
    if "Peers" in ordered:
        relevant.extend(peer_names[:4])
    if "History" in ordered and entity:
        relevant.append(f"{entity} 10-year history")

    return {
        "required": bool(ordered),
        "lenses": ordered,
        "compare_against": ordered,
        "relevant_comparisons": relevant,
        "summary": " + ".join(ordered) if ordered else "None",
        "confidence": 0.97 if ordered else 0.8,
    }
