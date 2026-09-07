"""Readiness gate — final institutional gate before any intelligence layer executes."""

from __future__ import annotations

import time
from typing import Any

from validation_engine.ambiguity_detector import detect_ambiguity
from validation_engine.blueprint_validator import validate_blueprint
from validation_engine.clarification_engine import build_clarifications
from validation_engine.confidence_validator import validate_confidence
from validation_engine.entity_validator import validate_entity
from validation_engine.evidence_validator import validate_evidence
from validation_engine.policy_engine import validate_policy
from validation_engine.question_validator import validate_question
from validation_engine.readiness_memo import build_readiness_memo
from validation_engine.routing_validator import validate_routing
from validation_engine.schema import (
    IVCE_VERSION,
    MANDATORY_OUTPUT_FIELDS,
    constitution_dict,
)


def _intent_status(question: str, body: dict[str, Any]) -> dict[str, Any]:
    ontology = body.get("research_ontology") or {}
    if "research_ontology" in ontology and isinstance(ontology.get("research_ontology"), dict):
        ontology = ontology["research_ontology"]
    objective = body.get("research_objective") or {}
    if "research_objective" in objective and isinstance(objective.get("research_objective"), dict):
        objective = objective["research_objective"]

    family = body.get("intent_family") or ontology.get("intent_family") or ontology.get("family")
    primary = (
        body.get("primary_objective")
        or objective.get("primary_objective")
        or ontology.get("primary_intent")
        or ontology.get("intent")
    )
    conf = float(ontology.get("confidence") or objective.get("confidence") or 0)
    q = question.lower()
    score = 0.7
    issues: list[str] = []
    if primary or family:
        score = max(0.85, conf or 0.85)
    else:
        # infer
        if any(x in q for x in ("explain", "what is", "define")):
            primary, family, score = "Educational", "educational", 0.9
        elif "compare" in q or " vs " in q:
            primary, family, score = "Peer Comparison", "company", 0.88
        elif "portfolio" in q:
            primary, family, score = "Portfolio Decision", "portfolio", 0.86
        elif "should i" in q:
            primary, family, score = "Investment Evaluation", "company", 0.9
        elif "rbi" in q or "macro" in q:
            primary, family, score = "Macro Impact", "macro", 0.88
        else:
            issues.append("intent_inferred")
            primary, family, score = "Investment Evaluation", "company", 0.72
    return {
        "status": "valid" if score >= 0.8 else "warning",
        "score": round(score, 4),
        "issues": issues,
        "primary_objective": primary,
        "intent_family": family,
    }


def _context_status(body: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    ctx = body.get("context_intelligence") or {}
    if "context_intelligence" in ctx and isinstance(ctx.get("context_intelligence"), dict):
        ctx = ctx["context_intelligence"]
    score = 0.75
    issues: list[str] = []
    if ctx:
        score = float(ctx.get("confidence") or 0.88)
        if ctx.get("missing_context"):
            issues.append("missing_context")
            score -= 0.1
    else:
        # educational needs less context
        if (intent.get("intent_family") or "") == "educational":
            score = 0.9
        else:
            issues.append("context_not_provided")
            score = 0.78
    return {
        "status": "valid" if score >= 0.8 else "warning",
        "score": round(max(0.0, min(1.0, score)), 4),
        "issues": issues,
    }


def validate_request(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    payload = body or {}

    # Optionally hydrate entity resolution if not provided
    ere = payload.get("entity_resolution") or {}
    if not ere:
        try:
            from entity_resolution.production import soft_slice_for_ask_agi as ere_soft

            ere = ere_soft(question, payload) or {}
        except Exception:
            ere = {}

    question_status = validate_question(question)
    entity_status = validate_entity(question, ere)
    intent_status = _intent_status(question, payload)
    context_status = _context_status(payload, intent_status)
    evidence_status = validate_evidence(
        question=question,
        primary_objective=str(intent_status.get("primary_objective") or ""),
        entity_status=entity_status,
        acquisition_planner=payload.get("acquisition_planner"),
        evidence_inventory=payload.get("evidence_inventory") if isinstance(payload.get("evidence_inventory"), dict) else None,
    )
    routing_status = validate_routing(
        question=question,
        analyst_router=payload.get("analyst_router"),
        layer_router=payload.get("layer_router"),
        primary_objective=str(intent_status.get("primary_objective") or ""),
    )
    blueprint_status = validate_blueprint(
        question=question,
        research_blueprint=payload.get("research_blueprint"),
        primary_objective=str(intent_status.get("primary_objective") or ""),
    )
    policy_status = validate_policy(
        question=question,
        primary_objective=str(intent_status.get("primary_objective") or ""),
        intent_family=str(intent_status.get("intent_family") or ""),
    )

    ambiguity = detect_ambiguity(
        question_status=question_status,
        entity_status=entity_status,
        intent_family=str(intent_status.get("intent_family") or ""),
    )
    clar = build_clarifications(
        question=question,
        ambiguity=ambiguity,
        question_status=question_status,
        entity_status=entity_status,
    )

    components = {
        "question": question_status,
        "entity": entity_status,
        "intent": intent_status,
        "context": context_status,
        "evidence": evidence_status,
        "routing": routing_status,
        "blueprint": blueprint_status,
        "policy": policy_status,
    }
    conf = validate_confidence(components=components)
    overall = float(conf["overall_readiness"])

    warnings: list[str] = []
    for key, row in components.items():
        for issue in row.get("issues") or []:
            if issue in {"blueprint_not_provided", "routing_not_provided", "context_not_provided", "intent_inferred"}:
                continue
            warnings.append(f"{key}: {issue}")
        for w in row.get("warnings") or []:
            warnings.append(str(w))

    # Determine readiness state
    blocked = (
        policy_status.get("status") == "blocked"
        or policy_status.get("score", 1) < 0.2
        or question_status.get("status") == "invalid"
        and "incomplete" in (question_status.get("issues") or [])
        and len((question or "").strip()) < 3
    )
    needs_clarification = bool(clar.get("required")) or entity_status.get("status") in {"clarification", "invalid"} and entity_status.get("needs_clarification")
    # Strong block: disallowed policy
    if policy_status.get("status") == "blocked":
        readiness_state = "BLOCKED"
        execution_allowed = False
    elif needs_clarification and overall < 0.75:
        readiness_state = "CLARIFICATION_REQUIRED"
        execution_allowed = False
    elif needs_clarification and any(
        f in (ambiguity.get("flags") or [])
        for f in ("ambiguous_entity", "missing_comparison_target", "too_many_entities", "incomplete")
    ):
        readiness_state = "CLARIFICATION_REQUIRED"
        execution_allowed = False
    elif warnings or evidence_status.get("status") == "warning" or overall < 0.9:
        if overall >= 0.7 and not needs_clarification:
            readiness_state = "READY_WITH_WARNINGS"
            execution_allowed = True
        elif overall >= 0.85:
            readiness_state = "READY_WITH_WARNINGS"
            execution_allowed = True
        else:
            readiness_state = "CLARIFICATION_REQUIRED" if needs_clarification else "READY_WITH_WARNINGS"
            execution_allowed = readiness_state != "CLARIFICATION_REQUIRED" and overall >= 0.65
    else:
        readiness_state = "READY"
        execution_allowed = True

    # Safety: never ready if clarification high-severity
    if ambiguity.get("severity") == "high" and clar.get("required"):
        readiness_state = "CLARIFICATION_REQUIRED"
        execution_allowed = False

    if blocked:
        readiness_state = "BLOCKED"
        execution_allowed = False

    memo = build_readiness_memo(
        question=question,
        readiness_state=readiness_state,
        overall_readiness=overall,
        components=components,
        warnings=warnings,
        routing_status=routing_status,
        evidence_status=evidence_status,
        entity_status=entity_status,
        expected_runtime_s=payload.get("expected_runtime_seconds"),
    )

    ms = (time.perf_counter() - t0) * 1000.0
    out = {
        "ok": True,
        "question": question,
        "question_status": question_status,
        "entity_status": entity_status,
        "intent_status": intent_status,
        "context_status": context_status,
        "evidence_status": evidence_status,
        "routing_status": routing_status,
        "blueprint_status": blueprint_status,
        "policy_status": policy_status,
        "overall_readiness": overall,
        "readiness_state": readiness_state,
        "warnings": warnings,
        "clarifications": clar.get("clarifications") or [],
        "confidence": conf.get("confidence"),
        "component_scores": conf.get("component_scores"),
        "ambiguity": ambiguity,
        "execution_allowed": execution_allowed,
        "readiness_memo": memo,
        "metrics": {
            "validation_ms": round(ms, 4),
            "clarification_required": readiness_state == "CLARIFICATION_REQUIRED",
            "blocked": readiness_state == "BLOCKED",
        },
        "ivce_version": IVCE_VERSION,
        "constitution_id": constitution_dict().get("id"),
        "not_a_top_level_intelligence_layer": True,
        "mandatory_fields_present": True,
    }
    out["mandatory_fields_present"] = all(f in out for f in MANDATORY_OUTPUT_FIELDS)
    return out
