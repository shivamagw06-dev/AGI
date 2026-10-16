"""Institutional Documents Dashboard."""

from __future__ import annotations

from typing import Any

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.schema import DOCUMENT_TYPES, IDI_VERSION


def documents_dashboard() -> dict[str, Any]:
    docs = store.list_documents()
    objects = store.list_objects()
    packs = store.list_packs()
    last = store.last_run() or {}
    companies = sorted({d.get("company") for d in docs if d.get("company")})
    by_type: dict[str, int] = {t: 0 for t in DOCUMENT_TYPES}
    for d in docs:
        t = d.get("type")
        if t in by_type:
            by_type[t] += 1
    latest = docs[:10]
    missing = []
    # Soft missing-report heuristic for catalog companies
    for company in ("INFY", "TCS", "RELIANCE"):
        have = {d.get("type") for d in docs if d.get("company") == company}
        for need in ("ANNUAL_REPORT", "QUARTERLY_REPORT"):
            if need not in have:
                missing.append({"company": company, "missing": need})

    return {
        "title": "Institutional Documents Dashboard",
        "version": IDI_VERSION,
        "north_star": "documents_as_first_class_evidence",
        "documents": len(docs),
        "coverage": {
            "companies": len(companies),
            "by_type": by_type,
            "object_count": len(objects),
            "pack_count": len(packs),
        },
        "latest_filings": [
            {
                "document_id": d.get("document_id"),
                "company": d.get("company"),
                "type": d.get("type"),
                "title": d.get("title"),
                "published_date": d.get("published_date"),
            }
            for d in latest
        ],
        "companies_updated": companies,
        "missing_reports": missing,
        "validation_failures": len([v for v in store.list_validations(limit=100) if not v.get("ok")]),
        "replay_status": "ready",
        "knowledge_objects_created": len(objects),
        "last_run": {
            "ingested_ok": last.get("ingested_ok"),
            "status": last.get("status"),
            "packs_created": last.get("packs_created"),
        },
        "recommendation": None,
        "fabricated": False,
    }
