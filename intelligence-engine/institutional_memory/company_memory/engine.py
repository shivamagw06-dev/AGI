"""Company memory — versioned multi-domain timeline."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company


def company_timeline(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "timeline": []}
    return {
        "found": True,
        "ticker": company["ticker"],
        "timeline": list(company.get("company_timeline") or []),
        "domains_covered": sorted({r.get("domain") for r in (company.get("company_timeline") or []) if r.get("domain")}),
        "rule": "Every opinion becomes versioned company memory",
    }
