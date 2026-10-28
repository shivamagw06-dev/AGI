"""8-step Institutional Knowledge Runtime pipeline."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_runtime.assertions import assertions_from_iko
from institutional_knowledge_runtime.confidence import calculate_confidence
from institutional_knowledge_runtime.contradictions import list_contradictions, resolve_contradictions
from institutional_knowledge_runtime.dependencies import resolve_dependencies
from institutional_knowledge_runtime.evidence import resolve_evidence
from institutional_knowledge_runtime.monitoring import evaluate_monitoring
from institutional_knowledge_runtime.schema import IKR_VERSION, PIPELINE_STEPS, PROGRAMME
from institutional_knowledge_runtime.validation import validate_assertions


def list_unknowns(iko: dict[str, Any]) -> list[dict[str, Any]]:
    """First-class unknown tracking."""
    out: list[dict[str, Any]] = []
    for claim in iko.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        if str(claim.get("state")) != "UNKNOWN":
            continue
        out.append({
            "assertion_id": claim.get("claim_id"),
            "reason": "Not yet researched",
            "priority": "high" if claim.get("required") is not False else "medium",
            "required_evidence": list(claim.get("evidence_required") or []),
            "expected_source": "evidence_pipeline",
            "responsible_engine": "company_dna",
            "statement": claim.get("statement"),
        })
    return out


def run_pipeline(
    iko: dict[str, Any],
    *,
    evidence_graph: dict[str, Any] | None = None,
    monitoring_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute full 8-step IKR pipeline."""
    steps_completed: list[str] = []

    # 1. Load Knowledge Object (already provided)
    steps_completed.append("load_object")

    # 2. Load Assertions
    assertions = assertions_from_iko(iko)
    steps_completed.append("load_assertions")

    # 3. Resolve Dependencies
    assertions = resolve_dependencies(assertions)
    steps_completed.append("resolve_dependencies")

    # 4. Resolve Evidence
    evidence_packs = resolve_evidence(assertions, evidence_graph)
    steps_completed.append("resolve_evidence")

    # 5. Resolve Contradictions
    assertions = resolve_contradictions(assertions, evidence_packs)
    steps_completed.append("resolve_contradictions")

    # 6. Evaluate Monitoring Rules
    assertions, monitoring_reports = evaluate_monitoring(assertions, metrics=monitoring_metrics)
    steps_completed.append("evaluate_monitoring")

    # 7. Calculate Assertion Confidence
    confidence_packs: dict[str, dict[str, Any]] = {}
    updated_assertions: list[dict[str, Any]] = []
    for a in assertions:
        aid = str(a.get("assertion_id"))
        pack = evidence_packs.get(aid)
        conf = calculate_confidence(a, pack)
        confidence_packs[aid] = conf
        ua = dict(a)
        if str(a.get("status")) != "UNKNOWN":
            ua["confidence"] = conf["result"]
        updated_assertions.append(ua)
    assertions = updated_assertions
    steps_completed.append("calculate_confidence")

    # 8. Return Validated Assertions
    validation = validate_assertions(assertions)
    unknowns = list_unknowns(iko)
    steps_completed.append("return_validated")

    return {
        "enabled": True,
        "version": IKR_VERSION,
        "programme": PROGRAMME,
        "entity_id": iko.get("entity_id"),
        "entity_type": iko.get("entity_type", "company"),
        "pipeline_steps": list(PIPELINE_STEPS),
        "steps_completed": steps_completed,
        "assertions": assertions,
        "evidence": evidence_packs,
        "confidence": confidence_packs,
        "monitoring": monitoring_reports,
        "unknowns": unknowns,
        "contradictions": list_contradictions(assertions),
        "validation": validation,
        "deterministic": True,
        "llm": False,
    }
