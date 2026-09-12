"""KIP v2 production facade — the only module the REST layer should import
from directly. Wraps every module behind plain functions returning
JSON-serializable dicts, and exposes health/observability endpoints.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from kip_v2.executive_summary import generate_executive_summary
from kip_v2.pipeline import ingest_document as _ingest_document
from kip_v2.retrieval import answer_question as _answer_question
from kip_v2.storage import get_store

logger = logging.getLogger("kip_v2")

KIP_V2_VERSION = "2.5.0"
PROGRAMME = "AGIB Phase 2.5 — Institutional Knowledge Intelligence (KIP v2)"

SUCCESS_METRIC_TARGETS = {
    "document_parsing_success_pct": 99.0,
    "fact_extraction_precision_pct": 95.0,
    "entity_resolution_pct": 99.0,
    "evidence_coverage_pct": 90.0,
    "unknown_entity_hallucination": 0,
    "comparison_failures": 0,
    "framework_leakage": 0,
    "executive_validation_pass_rate_pct": 99.0,
}


def health() -> dict[str, Any]:
    store = get_store()
    try:
        stats = store.stats()
        ok = True
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("kip_v2 health check failed")
        stats = {"error": str(exc)}
        ok = False
    return {
        "module": "kip_v2",
        "programme": PROGRAMME,
        "version": KIP_V2_VERSION,
        "status": "ok" if ok else "degraded",
        "modules": [
            "document_intelligence", "knowledge_builder", "financial_intelligence",
            "management_intelligence", "change_detection", "knowledge_graph", "evidence",
            "executive_summary", "retrieval", "incremental",
        ],
        "storage": stats,
        "checked_at": time.time(),
    }


def ingest(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    store = get_store()
    required = ("company_id", "company_name", "doc_type", "period", "title", "source", "text")
    missing = [f for f in required if not payload.get(f)]
    if missing:
        return {"error": "missing_required_fields", "missing": missing}
    try:
        result = _ingest_document(
            store,
            company_id=payload["company_id"],
            company_name=payload["company_name"],
            doc_type=payload["doc_type"],
            period=payload["period"],
            title=payload["title"],
            source=payload["source"],
            text=payload["text"],
            document_id=payload.get("document_id"),
            published_at=payload.get("published_at"),
            sector=payload.get("sector"),
            industry=payload.get("industry"),
            known_entities=payload.get("known_entities"),
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("kip_v2 ingest failed")
        return {"error": "ingest_failed", "detail": str(exc)}
    result["latency_ms"] = round((time.time() - started) * 1000, 2)
    return result


def get_knowledge(company_id: str, category: Optional[str] = None, key: Optional[str] = None) -> dict[str, Any]:
    store = get_store()
    facts = store.get_facts(company_id, category=category, key=key)
    return {"company_id": company_id, "count": len(facts), "facts": [f.to_dict() for f in facts]}


def get_financial_metrics(company_id: str, metric: Optional[str] = None, period: Optional[str] = None) -> dict[str, Any]:
    store = get_store()
    facts = store.get_facts(company_id, category="financial_metric", key=metric, period=period)
    return {"company_id": company_id, "count": len(facts), "metrics": [f.to_dict() for f in facts]}


def get_management_commentary(company_id: str, topic: Optional[str] = None) -> dict[str, Any]:
    store = get_store()
    facts = store.get_facts(company_id, category="management_statement", key=topic)
    return {"company_id": company_id, "count": len(facts), "statements": [f.to_dict() for f in facts]}


def get_changes(company_id: str, from_period: Optional[str] = None, to_period: Optional[str] = None) -> dict[str, Any]:
    store = get_store()
    deltas = store.get_deltas(company_id, from_period=from_period, to_period=to_period)
    return {"company_id": company_id, "count": len(deltas), "deltas": [d.to_dict() for d in deltas]}


def get_knowledge_graph(node_id: str) -> dict[str, Any]:
    store = get_store()
    nodes, edges = store.get_graph(node_id)
    return {
        "node_id": node_id,
        "nodes": [n.to_dict() for n in nodes],
        "edges": [e.to_dict() for e in edges],
    }


def get_executive_summary(company_id: str) -> dict[str, Any]:
    store = get_store()
    return generate_executive_summary(store, company_id)


def ask(company_id: str, question: str) -> dict[str, Any]:
    if not question or not question.strip():
        return {"error": "question_required"}
    store = get_store()
    return _answer_question(store, company_id, question)


def quality_report(company_id: Optional[str] = None) -> dict[str, Any]:
    """Computes as many of the Quality Contract / Success Metrics as can be
    derived from the current store contents. This reports on what has
    actually been ingested in this deployment — it is a live self-audit, not
    a claim about an un-ingested million-document corpus."""

    store = get_store()
    stats = store.stats()
    total_facts = stats.get("facts_active", 0) + stats.get("facts_archived", 0)
    rejections = stats.get("rejections", 0)
    attempted = total_facts + rejections
    precision_pct = round(100.0 * total_facts / attempted, 2) if attempted else None
    paragraphs = stats.get("paragraphs", 0)

    evidence_coverage_pct = None
    if company_id:
        from kip_v2.evidence import quality_contract_fields

        facts = store.get_facts(company_id, category=None, status=None)
        if facts:
            compliant = sum(1 for f in facts if quality_contract_fields(f.to_dict())[0])
            evidence_coverage_pct = round(100.0 * compliant / len(facts), 2)

    return {
        "programme": PROGRAMME,
        "targets": SUCCESS_METRIC_TARGETS,
        "observed": {
            "documents_ingested": stats.get("documents", 0),
            "paragraphs_indexed": paragraphs,
            "facts_stored": total_facts,
            "facts_rejected": rejections,
            "fact_extraction_precision_pct": precision_pct,
            "evidence_coverage_pct": evidence_coverage_pct,
            "graph_nodes": stats.get("graph_nodes", 0),
            "graph_edges": stats.get("graph_edges", 0),
            "change_deltas": stats.get("deltas", 0),
        },
        "note": "Every stored fact passed the Module 7 evidence gate (evidence, page, "
                "confidence, hash) unconditionally; facts_rejected counts candidates that "
                "failed that gate and were never stored.",
    }
