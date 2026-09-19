"""Build Opportunity Intelligence Pack from compiled inputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from opportunity_intelligence.blockers import detect_blockers
from opportunity_intelligence.catalysts import detect_catalysts
from opportunity_intelligence.dimensions import (
    extract_hypotheses,
    score_corporate,
    score_financial,
    score_macro,
    score_ownership,
    score_sector,
    score_technical,
    score_valuation,
)
from opportunity_intelligence.schema import (
    ENGINE_CODE,
    ENGINE_NAME,
    RECOMMENDATION_POLICY,
    VERSION,
    WORKSTREAM_ID,
)
from opportunity_intelligence.score import compose_score, explain_score_moves, research_priority
from opportunity_intelligence.util import as_float, display_ticker, resolve_ticker, round1
from opportunity_intelligence.why_now import build_why_now, strengths_from_dimensions


def build_opportunity_pack(
    ticker: str,
    *,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    t0 = datetime.now(timezone.utc)
    entity = resolve_ticker(ticker)
    memory = inputs.get("memory") if isinstance(inputs.get("memory"), dict) else {}
    delta = inputs.get("memory_delta") if isinstance(inputs.get("memory_delta"), dict) else None
    graph = inputs.get("knowledge_graph") if isinstance(inputs.get("knowledge_graph"), dict) else None
    scenarios = inputs.get("scenarios") if isinstance(inputs.get("scenarios"), dict) else None
    hyp = inputs.get("hypotheses") if isinstance(inputs.get("hypotheses"), dict) else None
    conf_pack = inputs.get("confidence") if isinstance(inputs.get("confidence"), dict) else None

    if not memory.get("ok"):
        return {
            "ok": False,
            "engine": ENGINE_CODE,
            "version": VERSION,
            "entity": entity,
            "display": display_ticker(entity),
            "error": memory.get("error") or "company_memory_unavailable",
            "recommendation_policy": RECOMMENDATION_POLICY,
            "issues_recommendations": False,
            "modifies_decision_engine": False,
        }

    valuation = score_valuation(memory)
    financial = score_financial(memory, delta)
    ownership = score_ownership(memory)
    corporate = score_corporate(memory)
    sector = score_sector(memory, graph)
    macro = score_macro(memory, graph, scenarios)
    catalysts, catalysts_dim = detect_catalysts(memory)
    technical = score_technical(memory)

    dimensions = {
        "valuation": valuation,
        "financial_momentum": financial,
        "ownership_momentum": ownership,
        "corporate_momentum": corporate,
        "sector_momentum": sector,
        "macro_context": macro,
        "catalysts": catalysts_dim,
    }

    blockers = detect_blockers(memory, dimensions=dimensions)
    score_pack = compose_score(dimensions, blockers=blockers, technical=technical)
    score = float(score_pack["score"])
    priority = research_priority(score, blockers)
    why_now = build_why_now(
        entity=display_ticker(entity),
        dimensions=dimensions,
        blockers=blockers,
        catalysts=catalysts,
        delta=delta,
        score=score,
        priority=priority,
    )
    strengths = strengths_from_dimensions(dimensions)
    supporting_h, contradicting_h = extract_hypotheses(hyp)
    explain = explain_score_moves(score_pack=score_pack, blockers=blockers, dimensions=dimensions)

    # Confidence: blend memory confidence + ICC soft + dimension coverage
    mem_conf = as_float(memory.get("confidence"))
    icc = as_float(
        (conf_pack or {}).get("confidence")
        or (conf_pack or {}).get("score")
        or ((conf_pack or {}).get("overall") or {}).get("confidence")
    )
    coverages = [as_float(d.get("coverage")) or 0.0 for d in dimensions.values()]
    avg_cov = sum(coverages) / max(1, len(coverages))
    conf_bits = [x for x in (mem_conf, icc, avg_cov / 100.0) if x is not None]
    # Normalise: memory/icc may be 0-1 or 0-100
    normed = []
    for x in conf_bits:
        normed.append(x / 100.0 if x > 1.0 else x)
    confidence = round1(100.0 * (sum(normed) / len(normed))) if normed else round1(avg_cov)

    evidence: list[dict[str, Any]] = []
    for key, dim in dimensions.items():
        for row in dim.get("evidence") or []:
            if isinstance(row, dict):
                evidence.append({"dimension": key, **row})
    evidence = evidence[:40]

    freshness = {
        "memory_compiled_at": memory.get("compiled_at"),
        "memory_version": memory.get("memory_version"),
        "delta_status": (delta or {}).get("status"),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }

    provenance = {
        "sources": [
            "company_memory",
            "knowledge_delta_engine",
            "investment_knowledge_graph",
            "institutional_scenario_intelligence",
            "hypothesis_engine",
            "institutional_confidence_calibration",
        ],
        "memory_version": memory.get("memory_version"),
        "memory_engine": memory.get("engine") or memory.get("version"),
        "graph_nodes": (graph or {}).get("n_nodes"),
        "graph_edges": (graph or {}).get("n_edges"),
        "raw_apis_queried": False,
    }

    latency_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)

    return {
        "ok": True,
        "enabled": True,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "entity": entity,
        "display": display_ticker(entity),
        "opportunity": {
            "score": score,
            "confidence": confidence,
            "research_priority": priority,
            "why_now": why_now,
            "strengths": strengths,
            "blockers": blockers,
            "catalysts": catalysts,
            "valuation": valuation,
            "financial_momentum": financial,
            "ownership_momentum": ownership,
            "corporate_momentum": corporate,
            "sector_momentum": sector,
            "macro_context": macro,
            "technical_context": technical,
            "supporting_hypotheses": supporting_h,
            "contradicting_hypotheses": contradicting_h,
            "evidence": evidence,
            "freshness": freshness,
            "provenance": provenance,
            "score_breakdown": score_pack,
            "explainability": explain,
            "knowledge_delta": {
                "status": (delta or {}).get("status"),
                "summary": (delta or {}).get("summary"),
                "n_field_changes": (delta or {}).get("n_field_changes"),
                "identical_to_prior": (delta or {}).get("identical_to_prior"),
            },
        },
        # Flat convenience mirrors for CID / APIs
        "score": score,
        "confidence": confidence,
        "research_priority": priority,
        "why_now": why_now,
        "strengths": strengths,
        "blockers": blockers,
        "catalysts": catalysts,
        "dimensions": dimensions,
        "technical_context": technical,
        "score_breakdown": score_pack,
        "explainability": explain,
        "freshness": freshness,
        "provenance": provenance,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "latency_ms": latency_ms,
    }
