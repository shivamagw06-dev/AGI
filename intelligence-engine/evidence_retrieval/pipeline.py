"""IERE main pipeline — Question → Discover → Retrieve → Rank → Assemble."""

from __future__ import annotations

import time
import uuid
from typing import Any

from evidence_retrieval.assembly import assemble_packs
from evidence_retrieval.citations import attach_citations
from evidence_retrieval.discovery import discover
from evidence_retrieval.graph import build_evidence_graph
from evidence_retrieval.provenance import retrieval_provenance
from evidence_retrieval.quality import evaluate_retrieval_gates
from evidence_retrieval.ranking import rank_evidence
from evidence_retrieval.retrieval import discover_candidates
from evidence_retrieval.schema import FREEZE_LOCKS, IERE_VERSION
from evidence_retrieval.store import record_run, utc_now


def retrieve_evidence(
    question: str,
    *,
    ticker_hint: str | None = None,
    as_of: str | None = None,
    top_n: int = 40,
) -> dict[str, Any]:
    t0 = time.time()
    retrieval_id = f"iere_{uuid.uuid4().hex[:12]}"
    discovery = discover(question, ticker_hint=ticker_hint, as_of=as_of)
    candidates = discover_candidates(discovery)
    # Defense-in-depth point-in-time filter (available_from <= as_of).
    pit = discovery.get("as_of")
    if pit:
        day = str(pit)[:10]
        candidates = [
            c for c in candidates if str(c.get("available_from") or "")[:10] <= day
        ]
    ranked = rank_evidence(candidates, discovery=discovery, as_of=discovery.get("as_of"))
    # Keep highest-ranked unique evidence; duplicates already penalised in ranking.
    ranked = [r for r in ranked if not r.get("duplicate")]
    ranked = attach_citations(ranked)
    packs = assemble_packs(ranked, retrieval_id=retrieval_id, discovery=discovery, top_n=top_n)
    graph = build_evidence_graph(
        retrieval_id=retrieval_id,
        discovery=discovery,
        ranked=ranked,
        pack_ids=[p["pack_id"] for p in packs],
    )
    gates = evaluate_retrieval_gates(
        ranked=ranked,
        packs=packs,
        graph=graph,
        as_of=discovery.get("as_of"),
    )

    # Ask/RO facing evidence pack envelope (structured only — never PDFs)
    ask_envelope = {
        "primary_engine": "evidence_retrieval",
        "retrieval_id": retrieval_id,
        "packs": {p["kind"]: p for p in packs},
        "top_evidence": ranked[: min(15, len(ranked))],
        "citations": [r.get("citation") for r in ranked[: min(15, len(ranked))]],
        "provenance": retrieval_provenance(),
        "fabricated": False,
        "pdf_sent_to_reasoning": False,
    }

    report = {
        "ok": bool(gates.get("passed")) or bool(ranked),
        "iere_version": IERE_VERSION,
        "retrieval_id": retrieval_id,
        "question": question,
        "discovery": discovery,
        "candidate_count": len(candidates),
        "ranked_count": len(ranked),
        "ranked": ranked,
        "packs": packs,
        "pack_ids": [p["pack_id"] for p in packs],
        "graph_id": graph.get("graph_id"),
        "graph": graph,
        "quality_gates": gates,
        "ask_envelope": ask_envelope,
        "latency_ms": int((time.time() - t0) * 1000),
        "finished_at": utc_now(),
        "freeze_locks": FREEZE_LOCKS,
        "reasoning_changed": False,
        "governance_changed": False,
        "fabricated": False,
        "recommendation": None,
    }
    record_run(report)
    return report
