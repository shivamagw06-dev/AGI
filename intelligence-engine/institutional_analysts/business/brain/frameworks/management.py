"""Framework 8 — Management quality (business-mandate lens only)."""

from __future__ import annotations

from typing import Any

from institutional_analysts.business.brain._text import as_list, blob_of, txt


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    """Assess management signals available in assembled evidence.

    Does not replace the Management Analyst mandate — only captures business-relevant
    capital discipline and long-term orientation signals already present.
    """
    name = evidence.get("company") or "the company"
    capital = txt(evidence.get("capital_allocation"))
    mgmt = evidence.get("management") if isinstance(evidence.get("management"), dict) else {}
    governance = txt(mgmt.get("governance") or evidence.get("governance"))
    docs = as_list(evidence.get("documents_used") or [e.get("claim") for e in (evidence.get("evidence_refs") or []) if isinstance(e, dict)], limit=4)
    b = blob_of(capital, governance, docs)

    execution = (
        "Execution track record appears institutionally consistent"
        if any(k in b for k in ("disciplin", "conservative", "track record", "institutional"))
        else "Execution quality inferred from capital allocation language — needs ongoing confirmation"
    )
    communication = (
        "Communication artefacts (reports / presentations / commentary) are present in the file"
        if docs
        else "Limited direct management communication artefacts in the current file"
    )
    long_term = (
        "Capital allocation language emphasises multi-year franchise building"
        if any(k in b for k in ("long-term", "reinvestment", "franchise", "disciplin", "conservative"))
        else "Long-term orientation not yet strongly evidenced"
    )
    discipline = capital or "Capital discipline must be judged by reinvestment returns and balance-sheet choices over time."

    return {
        "framework": "Management (business lens)",
        "completed": bool(capital or governance or docs),
        "sources_reviewed": docs or ["Institutional research file"],
        "execution": execution,
        "communication": communication,
        "long_term_thinking": long_term,
        "capital_discipline": discipline,
        "assessment": (
            f"From a business-quality perspective, {name}'s ownership case strengthens when management "
            f"pairs franchise reinvestment with capital discipline — {discipline.lower().rstrip('.')}."
        ),
    }
