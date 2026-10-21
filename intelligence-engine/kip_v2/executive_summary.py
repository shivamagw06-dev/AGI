"""Module 8 — Executive Summary Generator.

Generates a structured executive summary (Company Overview, Business Model,
Financial Performance, Operational Highlights, Capital Allocation,
Management Commentary, Risks, Outlook, Key KPIs) EXCLUSIVELY from facts
already sitting in the Knowledge Store. This module never touches
``Document.text`` — that is the literal enforcement of Core Principle 1
("never summarize raw documents directly") and Module 8's own contract
("never read directly from the original PDF").

Sections with zero supporting facts are marked ``"unknown"`` rather than
fabricated (Core Principle 6/7).
"""

from __future__ import annotations

from typing import Any

from kip_v2.storage.base import KnowledgeStore

_SECTION_CATEGORY_MAP: dict[str, list[str]] = {
    "business_model": ["business_model", "products", "segments"],
    "financial_performance": [],  # populated from financial_metric facts directly
    "operational_highlights": ["revenue_drivers", "cost_drivers", "customers", "suppliers", "competition"],
    "capital_allocation": ["capital_allocation", "mna"],
    "management_commentary": [],  # populated from management_statement facts directly
    "risks": ["risks"],
    "outlook": ["strategy"],
    "key_kpis": ["financial_kpis"],
}

_TOP_N_PER_SECTION = 5


def _section_entries(store: KnowledgeStore, company_id: str, categories: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for category in categories:
        for fact in store.get_facts(company_id, category=category):
            entries.append(
                {
                    "text": fact.value,
                    "confidence": fact.confidence,
                    "period": fact.period,
                    "evidence": {
                        "document_id": fact.evidence.document_id,
                        "page": fact.evidence.page,
                        "snippet": fact.evidence.snippet,
                        "evidence_hash": fact.evidence.evidence_hash,
                    },
                }
            )
    entries.sort(key=lambda e: e["confidence"], reverse=True)
    return entries[:_TOP_N_PER_SECTION]


def _financial_performance(store: KnowledgeStore, company_id: str) -> list[dict[str, Any]]:
    entries = []
    for fact in store.get_facts(company_id, category="financial_metric"):
        entries.append(
            {
                "metric": fact.key,
                "value": fact.value,
                "unit": fact.unit,
                "currency": fact.currency,
                "period": fact.period,
                "confidence": fact.confidence,
                "evidence": {
                    "document_id": fact.evidence.document_id,
                    "page": fact.evidence.page,
                    "snippet": fact.evidence.snippet,
                },
            }
        )
    entries.sort(key=lambda e: (e["metric"], e["period"] or ""))
    return entries


def _management_commentary(store: KnowledgeStore, company_id: str) -> list[dict[str, Any]]:
    entries = []
    for fact in store.get_facts(company_id, category="management_statement"):
        entries.append(
            {
                "topic": fact.key,
                "quote": fact.value,
                "speaker": (fact.extra or {}).get("speaker"),
                "sentiment": (fact.extra or {}).get("sentiment"),
                "confidence": fact.confidence,
                "period": fact.period,
                "evidence": {
                    "document_id": fact.evidence.document_id,
                    "page": fact.evidence.page,
                    "snippet": fact.evidence.snippet,
                },
            }
        )
    entries.sort(key=lambda e: e["confidence"], reverse=True)
    return entries[: _TOP_N_PER_SECTION * 2]


def generate_executive_summary(store: KnowledgeStore, company_id: str) -> dict[str, Any]:
    summary: dict[str, Any] = {"company_id": company_id, "sections": {}}
    known_sections = 0

    for section, categories in _SECTION_CATEGORY_MAP.items():
        if section == "financial_performance":
            entries = _financial_performance(store, company_id)
        elif section == "management_commentary":
            entries = _management_commentary(store, company_id)
        else:
            entries = _section_entries(store, company_id, categories)

        if entries:
            known_sections += 1
            summary["sections"][section] = {"status": "known", "entries": entries}
        else:
            summary["sections"][section] = {"status": "unknown", "entries": []}

    summary["coverage"] = round(known_sections / len(_SECTION_CATEGORY_MAP), 3)
    summary["generated_from"] = "structured_knowledge_only"
    return summary
