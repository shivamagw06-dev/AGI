"""Evidence history — historical evidence retained across versions."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company


def evidence_evolution(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "history": []}
    hist = list(company.get("evidence_history") or [])
    retained = all(bool(h.get("retained", True)) for h in hist) if hist else False
    return {
        "found": True,
        "ticker": company["ticker"],
        "history": hist,
        "historical_evidence_retained": retained and len(hist) >= 1,
        "item_count": sum(len(h.get("items") or []) for h in hist),
        "rule": "Historical evidence retained — never discarded on thesis update",
    }
