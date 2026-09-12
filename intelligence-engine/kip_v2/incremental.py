"""Module 10 — Incremental Learning helpers.

Two distinct kinds of "new information" are handled:

1. **Same document re-ingested** (identical ``document_id``, e.g. a retry):
   ``paragraph_exists`` (evidence_hash scoped to the document) makes
   paragraph storage and downstream extraction naturally idempotent — no
   duplicate facts, no wasted re-processing.

2. **A revised version of the same report** (same company/doc_type/period,
   but a new ``document_id`` because the source changed — e.g. a restated
   annual report): facts extracted from the new document that share
   company/category/key/period with an existing *active* fact from the
   superseded document are archived via ``supersede_fact`` rather than left
   to accumulate as duplicates.

Period-over-period knowledge (e.g. FY26 vs FY25) is intentionally NOT
archived here — that is genuine historical time series and is handled by
Module 5 (Change Detection), which the pipeline also invokes automatically
on ingestion of a new period for the same company/doc_type.
"""

from __future__ import annotations

from typing import Optional

from kip_v2.schema import Document, Fact
from kip_v2.storage.base import KnowledgeStore


def find_prior_same_report_version(
    store: KnowledgeStore, company_id: str, doc_type: str, period: str, exclude_document_id: str
) -> Optional[Document]:
    """A previously ingested document with the same company/doc_type/period
    but a different id — i.e. a restated/updated version of the same report."""

    candidates = [
        d for d in store.list_documents(company_id)
        if d.doc_type == doc_type and d.period == period and d.document_id != exclude_document_id
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda d: d.ingested_at)[-1]


def find_prior_period_document(
    store: KnowledgeStore, company_id: str, doc_type: str, exclude_period: str
) -> Optional[Document]:
    """The most recent previously ingested document of the same type but a
    different period — used to trigger Module 5 change detection."""

    candidates = [
        d for d in store.list_documents(company_id)
        if d.doc_type == doc_type and d.period != exclude_period
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda d: d.ingested_at)[-1]


def supersede_matching_facts(store: KnowledgeStore, old_document_id: str, new_facts: list[Fact]) -> int:
    """For each new fact, archive any active fact from ``old_document_id``
    sharing (company_id, category, key, period). Returns count archived."""

    archived = 0
    for new_fact in new_facts:
        candidates = store.get_facts(
            new_fact.company_id, category=new_fact.category, key=new_fact.key, period=new_fact.period
        )
        for old_fact in candidates:
            if old_fact.source_document_id == old_document_id and old_fact.fact_id != new_fact.fact_id:
                store.supersede_fact(old_fact.fact_id, new_fact.fact_id)
                archived += 1
    return archived
