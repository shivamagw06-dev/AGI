"""Thesis memory — every version preserved; never overwrite."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company
from institutional_memory.versioning.rules import assert_append_only


def thesis_history(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "theses": []}
    theses = list(company.get("theses") or [])
    gate = assert_append_only(theses)
    evolution = [
        {
            "version": t.get("version"),
            "date": t.get("date"),
            "stance": t.get("stance"),
            "confidence": t.get("confidence"),
            "outcome": t.get("outcome"),
            "why": t.get("outcome_note") or t.get("evidence"),
        }
        for t in theses
    ]
    return {
        "found": True,
        "ticker": company["ticker"],
        "theses": theses,
        "evolution": evolution,
        "no_overwrite": gate.get("no_overwrite"),
        "append_only": gate.get("append_only"),
        "rule": "Never overwrite — every thesis version retained",
    }
