"""Committee memory — consensus, minority, votes, challenges preserved."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company
from institutional_memory.versioning.rules import assert_append_only


def committee_history(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "decisions": []}
    decisions = list(company.get("committee_decisions") or [])
    gate = assert_append_only(decisions)
    qualities = [float(d["outcome_quality"]) for d in decisions if d.get("outcome_quality") is not None]
    minority_hits = [d for d in decisions if d.get("minority_was_correct") is True]
    return {
        "found": True,
        "ticker": company["ticker"],
        "decisions": decisions,
        "append_only": gate.get("append_only"),
        "consensus_accuracy": round(sum(qualities) / len(qualities), 3) if qualities else None,
        "minority_accuracy_cases": len(minority_hits),
        "decision_quality": round(sum(qualities) / len(qualities), 3) if qualities else None,
        "evolution": [
            {
                "date": d.get("date"),
                "consensus": d.get("consensus"),
                "minority": d.get("minority"),
                "decision": d.get("decision"),
                "outcome_quality": d.get("outcome_quality"),
            }
            for d in decisions
        ],
        "rule": "Every committee decision preserved",
    }
