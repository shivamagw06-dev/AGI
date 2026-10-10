"""11-step Institutional Knowledge Factory pipeline."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_factory.assertion_compiler import compile_assertions
from institutional_knowledge_factory.decision_memory import version_decision_memory
from institutional_knowledge_factory.dna_update import update_company_dna
from institutional_knowledge_factory.evidence_graph import apply_delta, get_graph_pack
from institutional_knowledge_factory.notifications import notify_research_workflows
from institutional_knowledge_factory.quality import compute_knowledge_quality
from institutional_knowledge_factory.review import institutional_review
from institutional_knowledge_factory.schema import IKF_VERSION, PIPELINE_STEPS, PROGRAMME
from institutional_knowledge_factory.sources import normalize_sources
from institutional_knowledge_factory.thesis import evaluate_thesis
from institutional_knowledge_runtime.assertions import claim_to_assertion
from institutional_knowledge_runtime.contradictions import resolve_contradictions
from institutional_knowledge_runtime.store import put


def process_evidence(
    entity_id: str,
    evidence_items: list[dict[str, Any]],
    *,
    company: str | None = None,
    reason: str = "Evidence pipeline ingestion",
) -> dict[str, Any]:
    """Run full IKF pipeline on incoming evidence."""
    steps_completed: list[str] = []

    # 1. Collect
    collected = [e for e in evidence_items if isinstance(e, dict)]
    steps_completed.append("collect")

    # 2. Normalize
    normalized = normalize_sources(collected)
    steps_completed.append("normalize")

    # 3–5. Assertion Compiler (extract + validate)
    valid_claims, extracted, validation_reports = compile_assertions(normalized)
    steps_completed.extend(["extract", "identify_claims", "validate_evidence"])

    # 6. Resolve Contradictions (pre-update)
    assertions = [claim_to_assertion(c) for c in valid_claims]
    resolved = resolve_contradictions(assertions)
    contradiction_map = {str(a["assertion_id"]): a for a in resolved}
    for claim in valid_claims:
        cid = claim.get("claim_id")
        if cid and cid in contradiction_map:
            claim["state"] = contradiction_map[cid].get("status", claim.get("state"))
    steps_completed.append("resolve_contradictions")

    # 7. Update Assertions + 8. Update Company DNA
    iko, changes = update_company_dna(entity_id, valid_claims, company=company, reason=reason)
    steps_completed.extend(["update_assertions", "update_company_dna"])

    # 9. Update Monitoring (monitoring attached during extract/update)
    monitoring_updates = sum(1 for c in valid_claims if c.get("monitoring"))
    steps_completed.append("update_monitoring")

    # 10. Version Decision Memory
    thesis = evaluate_thesis(iko, changes)
    iko = version_decision_memory(entity_id, iko, changes, thesis)
    put("company", entity_id, iko)
    steps_completed.append("version_decision_memory")

    # Quality + Review
    quality = compute_knowledge_quality(iko)
    review = institutional_review(iko, changes, quality)

    # 11. Notify Research Workflows
    notifications = notify_research_workflows(
        entity_id,
        changes=changes,
        thesis=thesis,
        review=review,
        quality=quality,
    )
    steps_completed.append("notify_research_workflows")

    # KPE-owned Evidence Graph (writes only — apps never query directly)
    evidence_delta = []
    for source in normalized:
        for claim in valid_claims:
            for ref in claim.get("evidence_refs") or []:
                if isinstance(ref, dict):
                    evidence_delta.append({
                        "evidence_id": ref.get("evidence_id"),
                        "source_id": source.get("source_id"),
                        "entity_id": entity_id.upper(),
                        "claim_id": claim.get("claim_id"),
                        "trust_score": source.get("trust_score"),
                        "freshness": source.get("freshness"),
                        "provenance": "kpe_incremental",
                    })
    if evidence_delta:
        apply_delta(entity_id, evidence_delta)
    graph_pack = get_graph_pack(entity_id)

    return {
        "enabled": True,
        "version": IKF_VERSION,
        "programme": PROGRAMME,
        "entity_id": entity_id.upper(),
        "entity_type": "company",
        "pipeline_steps": list(PIPELINE_STEPS),
        "steps_completed": steps_completed,
        "sources_processed": len(normalized),
        "claims_extracted": len(extracted),
        "claims_validated": len(valid_claims),
        "claims_updated": len(changes),
        "monitoring_updates": monitoring_updates,
        "validation_reports": validation_reports,
        "changes": changes,
        "iko": iko,
        "thesis": thesis,
        "quality": quality,
        "review": review,
        "notifications": notifications,
        "evidence_graph_delta": evidence_delta,
        "evidence_graph": graph_pack,
        "deterministic": True,
        "llm": False,
        "llm_used": False,
    }
