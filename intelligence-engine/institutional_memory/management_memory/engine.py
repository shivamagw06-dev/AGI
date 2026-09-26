"""Management memory — guidance, capital allocation, credibility history."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company
from institutional_memory.versioning.rules import assert_append_only


def management_history(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "history": []}
    rows = list(company.get("management") or [])
    gate = assert_append_only(rows)
    return {
        "found": True,
        "ticker": company["ticker"],
        "history": rows,
        "append_only": gate.get("append_only"),
        "latest": rows[-1] if rows else None,
    }
