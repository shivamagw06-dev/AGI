"""KIP v2 — Institutional Knowledge Intelligence (AGIB Phase 2.5).

Transforms AGI from a retrieval-based assistant into an institutional research
platform: documents are learned ONCE, structured knowledge is stored durably,
and future questions are answered from evidence — never by re-summarizing raw
documents.

Core principles (enforced in code, not just docs):
    1. Never summarize raw documents directly     -> executive_summary.py reads
       only from the structured store, never from Document.text.
    2. Parse -> Extract -> Structure -> Validate -> Store -> Answer
       -> document_intelligence.py -> knowledge_builder.py /
          financial_intelligence.py / management_intelligence.py ->
          evidence.py -> storage/ -> retrieval.py
    3. Every factual claim must be traceable to evidence -> evidence.py's
       validate_fact() is a hard gate in front of every store_* call.
    4. Knowledge persists across sessions -> storage/sqlite_store.py (default,
       real on-disk persistence) or storage/postgres_store.py (pgvector,
       production Supabase/Postgres) behind the same KnowledgeStore contract.
    5. Executive Composer consumes structured knowledge, not PDFs.
    6. Unknown facts must remain unknown -> retrieval.py returns
       unknown=True instead of guessing when evidence is insufficient.
    7. Never fabricate -> no LLM is used anywhere in the extraction or
       validation path; all extraction is deterministic (regex / lexicon /
       heuristic), matching the rest of the AGIB accounting/analyst stack.

Modules (file -> spec module number):
    document_intelligence.py   Module 1  Document Intelligence Engine
    knowledge_builder.py       Module 2  Structured Knowledge Builder
    financial_intelligence.py  Module 3  Financial Intelligence
    management_intelligence.py Module 4  Management Intelligence
    change_detection.py        Module 5  Change Detection
    knowledge_graph.py         Module 6  Knowledge Graph
    evidence.py                Module 7  Evidence Validation
    executive_summary.py       Module 8  Executive Summary Generator
    retrieval.py               Module 9  Knowledge Retrieval
    incremental.py             Module 10 Incremental Learning
    pipeline.py                 orchestrates 1 -> 2/3/4 -> 7 -> store -> 10
    production.py                REST-facing facade + observability
"""

from kip_v2.production import health

KIP_V2_VERSION = "2.5.0"
PROGRAMME = "AGIB Phase 2.5 — Institutional Knowledge Intelligence (KIP v2)"

__all__ = ["health", "KIP_V2_VERSION", "PROGRAMME"]
