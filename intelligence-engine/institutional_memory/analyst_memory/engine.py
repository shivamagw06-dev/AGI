"""Analyst memory — opinions, reasoning, accuracy evolution."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company
from institutional_memory.versioning.rules import assert_append_only


def analyst_history(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "opinions": []}
    opinions = list(company.get("analyst_opinions") or [])
    gate = assert_append_only(opinions)
    by_role: dict[str, list[dict[str, Any]]] = {}
    for o in opinions:
        by_role.setdefault(str(o.get("role") or "unknown"), []).append(o)
    scored = [o for o in opinions if o.get("accuracy") is not None]
    mean_acc = round(sum(float(o["accuracy"]) for o in scored) / len(scored), 3) if scored else None
    return {
        "found": True,
        "ticker": company["ticker"],
        "opinions": opinions,
        "by_role": by_role,
        "mean_accuracy": mean_acc,
        "append_only": gate.get("append_only"),
        "historical_evolution": [
            {
                "date": o.get("date"),
                "role": o.get("role"),
                "confidence": o.get("confidence"),
                "accuracy": o.get("accuracy"),
                "opinion": o.get("opinion"),
            }
            for o in opinions
        ],
    }
