"""Top-level orchestrator: Document -> ... -> Answer.

``ingest_document`` is the single entry point that wires Modules 1, 2, 3, 4,
6, 7 and 10 together, and automatically triggers Module 5 (Change Detection)
when a new period arrives for a company/doc_type pair already known to the
store. Modules 8 and 9 (Executive Summary / Retrieval) are pure readers of
the resulting store and are invoked separately (see ``production.py``).
"""

from __future__ import annotations

from typing import Any, Optional

from kip_v2.change_detection import detect_changes
from kip_v2.document_intelligence import process_document
from kip_v2.financial_intelligence import build_financial_facts
from kip_v2.incremental import (
    find_prior_period_document,
    find_prior_same_report_version,
    supersede_matching_facts,
)
from kip_v2.knowledge_builder import build_knowledge_facts
from kip_v2.knowledge_graph import company_node, graph_from_facts
from kip_v2.management_intelligence import build_management_facts
from kip_v2.storage.base import KnowledgeStore


def ingest_document(
    store: KnowledgeStore,
    *,
    company_id: str,
    company_name: str,
    doc_type: str,
    period: str,
    title: str,
    source: str,
    text: str,
    document_id: Optional[str] = None,
    published_at: Optional[str] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    known_entities: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    result = process_document(
        company_id=company_id, doc_type=doc_type, period=period, title=title, source=source,
        text=text, document_id=document_id, published_at=published_at, known_entities=known_entities,
    )
    document = result.document

    prior_same_report = find_prior_same_report_version(store, company_id, doc_type, period, document.document_id)
    prior_period_doc = find_prior_period_document(store, company_id, doc_type, exclude_period=period)

    store.store_document(document)

    new_paragraphs = [p for p in result.paragraphs if store.store_paragraph(p)]

    knowledge_facts = build_knowledge_facts(company_id, new_paragraphs, period=period)
    financial_facts = build_financial_facts(company_id, new_paragraphs, default_period=period)
    management_facts = build_management_facts(company_id, new_paragraphs, period=period)

    all_candidate_facts = knowledge_facts + financial_facts + management_facts
    stored_facts = []
    rejected = 0
    rejection_reasons: list[str] = []
    for fact in all_candidate_facts:
        ok, errors = store.store_fact(fact)
        if ok:
            stored_facts.append(fact)
        else:
            rejected += 1
            rejection_reasons.extend(errors)

    archived_count = 0
    if prior_same_report is not None and stored_facts:
        archived_count = supersede_matching_facts(store, prior_same_report.document_id, stored_facts)

    nodes, edges = company_node(company_id, company_name, sector=sector, industry=industry)
    g_nodes, g_edges = graph_from_facts(company_id, stored_facts)
    nodes.extend(g_nodes)
    edges.extend(g_edges)
    for node in nodes:
        store.upsert_node(node)
    for edge in edges:
        store.upsert_edge(edge)

    deltas_stored = 0
    if prior_period_doc is not None:
        old_facts = store.get_facts(company_id, category=None, period=prior_period_doc.period)
        deltas = detect_changes(company_id, prior_period_doc.period, period, old_facts, stored_facts)
        for delta in deltas:
            store.store_delta(delta)
        deltas_stored = len(deltas)

    return {
        "document_id": document.document_id,
        "company_id": company_id,
        "paragraphs_parsed": len(result.paragraphs),
        "paragraphs_new": len(new_paragraphs),
        "facts_extracted": len(all_candidate_facts),
        "facts_stored": len(stored_facts),
        "facts_rejected": rejected,
        "rejection_reasons": rejection_reasons,
        "graph_nodes_upserted": len(nodes),
        "graph_edges_upserted": len(edges),
        "prior_version_archived_facts": archived_count,
        "change_deltas_detected": deltas_stored,
        "compared_against_period": prior_period_doc.period if prior_period_doc else None,
        "pipeline_stats": result.stats,
    }
