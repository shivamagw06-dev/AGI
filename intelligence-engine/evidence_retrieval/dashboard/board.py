"""Mission Control / API dashboard for IERE."""

from __future__ import annotations

from typing import Any

from evidence_retrieval.citations.builder import citation_coverage
from evidence_retrieval.schema import FREEZE_LOCKS, IERE_VERSION, MODULE_CODE, PROGRAMME
from evidence_retrieval.store import last_run


def evidence_dashboard() -> dict[str, Any]:
    run = last_run() or {}
    ranked = run.get("ranked") or []
    packs = run.get("packs") or []
    cit = citation_coverage(ranked)
    gates = run.get("quality_gates") or {}
    discovery = run.get("discovery") or {}
    types = sorted({str(r.get("evidence_type")) for r in ranked if r.get("evidence_type")})
    confidences = [float(r.get("confidence") or 0) for r in ranked]
    avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    freshness_scores = [
        float((r.get("rank_scores") or {}).get("freshness") or 0) for r in ranked
    ]
    avg_fresh = round(sum(freshness_scores) / len(freshness_scores), 4) if freshness_scores else 0.0

    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "version": IERE_VERSION,
        "evidence_coverage": {
            "ranked_count": len(ranked),
            "pack_count": len(packs),
            "evidence_types": types,
            "companies": discovery.get("companies") or [],
        },
        "evidence_freshness": avg_fresh,
        "retrieval_latency_ms": run.get("latency_ms"),
        "citation_coverage": cit.get("coverage"),
        "citation_complete": cit.get("complete"),
        "replay_health": {
            "as_of": discovery.get("as_of"),
            "future_leakage": "future_leakage" in (gates.get("failures") or []),
            "ok": "future_leakage" not in (gates.get("failures") or []),
        },
        "knowledge_completeness": round(min(1.0, len(types) / 8.0), 4) if types else 0.0,
        "evidence_confidence": avg_conf,
        "quality_gates": gates,
        "last_retrieval_id": run.get("retrieval_id"),
        "north_star": "Every AGIB question retrieves ranked institutional evidence packs",
        "freeze_locks": FREEZE_LOCKS,
        "fabricated": False,
    }


def build_dashboard() -> dict[str, Any]:
    return evidence_dashboard()


def build_health() -> dict[str, Any]:
    from evidence_retrieval.production import health

    return health()
