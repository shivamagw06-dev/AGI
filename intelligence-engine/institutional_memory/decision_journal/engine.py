"""Decision journal — question → evidence → alternatives → outcome → lessons."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company
from institutional_memory.versioning.rules import assert_append_only


def decision_journal(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "entries": []}
    entries = list(company.get("decisions") or [])
    gate = assert_append_only(entries)
    return {
        "found": True,
        "ticker": company["ticker"],
        "entries": entries,
        "append_only": gate.get("append_only"),
        "lessons_extracted": [e.get("lessons") for e in entries if e.get("lessons")],
        "rule": "Every institutional decision stores question, evidence, alternatives, outcome, lessons",
    }
