"""Module 7 — Institutional Planner.

Question → Intent → Evidence Contract → Applicable Frameworks
→ Execution Order → Conflict Rules → Committee
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.evidence_contracts import contract_for
from institutional_reasoning.iki.applicability import score_applicability
from institutional_reasoning.iki.confidence import confidence_for
from institutional_reasoning.iki.debate import debate
from institutional_reasoning.iki.decision_policies import policy_for
from institutional_reasoning.iki.graph_relations import soft_ikg_slice
from institutional_reasoning.iki.mental_models import evaluate_authors
from institutional_reasoning.iki.registry import get_framework
from institutional_reasoning.iki.schema import IKI_VERSION

PLANNER_VERSION = "institutional-planner-v1.0.0"
EXECUTION_SCORE_FLOOR = 45.0


def plan(
    *,
    question: str,
    question_type: str,
    entity: dict[str, Any] | None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ent = entity or {}
    entity_id = ent.get("entity_id")
    entity_type = ent.get("entity_type")
    contract = contract_for(question_type)
    applicability = score_applicability(
        question_type=question_type,
        entity_id=entity_id,
        entity_type=entity_type,
    )
    # Execution order: applicable first by score, then high-priority rejected for explicit N/A records
    # Phase 7 — soft planner overlay may re-rank without rewriting framework source.
    cal_weights: dict[str, float] = {}
    try:
        from institutional_reasoning.cal.overlays import planner_weights as cal_planner_weights

        cal_weights = dict((cal_planner_weights().get("weights") or {}))
    except Exception:
        cal_weights = {}
    to_run: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in applicability.get("applicable") or []:
        fid = row["framework_id"]
        if fid in seen:
            continue
        spec = get_framework(fid)
        if not spec:
            continue
        seen.add(fid)
        base_score = float(row.get("score") or 0)
        overlay_w = float(cal_weights.get(fid) or 0) or None
        ranked = base_score * (overlay_w if overlay_w is not None else 1.0)
        to_run.append(
            {
                "framework_id": fid,
                "name": spec.name,
                "author": spec.author,
                "version": spec.version,
                "requires": list(spec.requires),
                "produces": list(spec.produces),
                "priority": spec.priority,
                "applicability_score": row.get("score"),
                "planner_overlay_weight": overlay_w,
                "ranked_score": ranked,
                "applicability_reasons": row.get("reasons"),
                "confidence": confidence_for(fid),
                "invalid_for_entity_types": list(spec.not_applicable_entity_types),
                "invalid_for_sectors": list(spec.not_applicable_sectors),
                "school": spec.school,
                "competing_frameworks": list(spec.competing_frameworks),
                "alternative_frameworks": list(spec.alternative_frameworks),
            }
        )
    if cal_weights:
        to_run.sort(key=lambda r: float(r.get("ranked_score") or 0), reverse=True)
    # Always surface key rejected frameworks (DCF on banks, Graham on Zomato) for explainability
    for row in applicability.get("rejected") or []:
        fid = row["framework_id"]
        if fid in seen:
            continue
        if float(row.get("score") or 0) > 0 and fid not in {
            "dcf_applicability",
            "dcf_fcff",
            "margin_of_safety",
            "graham_net_net",
            "buffett_quality",
            "residual_income",
        }:
            continue
        # include important rejects
        if fid in {
            "dcf_applicability",
            "dcf_fcff",
            "margin_of_safety",
            "graham_net_net",
            "buffett_quality",
            "residual_income",
        } or float(row.get("score") or 0) == 0:
            spec = get_framework(fid)
            if not spec:
                continue
            # Only add rejects relevant to this question family
            if question_type not in spec.question_types and question_type != "valuation":
                continue
            seen.add(fid)
            to_run.append(
                {
                    "framework_id": fid,
                    "name": spec.name,
                    "author": spec.author,
                    "version": spec.version,
                    "requires": list(spec.requires),
                    "produces": list(spec.produces),
                    "priority": spec.priority,
                    "applicability_score": row.get("score"),
                    "applicability_reasons": row.get("reasons"),
                    "confidence": confidence_for(fid),
                    "invalid_for_entity_types": list(spec.not_applicable_entity_types),
                    "invalid_for_sectors": list(spec.not_applicable_sectors),
                    "school": spec.school,
                    "pre_rejected": True,
                    "pre_reject_reasons": row.get("reasons"),
                    "alternatives": row.get("alternatives"),
                    "competing_frameworks": list(spec.competing_frameworks),
                    "alternative_frameworks": list(spec.alternative_frameworks),
                }
            )

    authors = evaluate_authors(str(entity_id or ""), evidence)
    return {
        "planner_version": PLANNER_VERSION,
        "iki_version": IKI_VERSION,
        "question": str(question or "")[:500],
        "intent": question_type,
        "evidence_contract": contract.to_dict(),
        "applicability": applicability,
        "execution_order": to_run,
        "decision_policy": policy_for(question_type),
        "authors": authors,
        "ikg_slice": soft_ikg_slice(to_run[0]["framework_id"] if to_run else "rel_val_damodaran"),
        "conflict_rules": {
            "retain_all_executed": True,
            "never_average_away_disagreement": True,
            "explain_cross_author": True,
        },
    }


def finalize_with_debate(
    plan_record: dict[str, Any],
    *,
    framework_results: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    d = debate(
        question_type=str(plan_record.get("intent") or "valuation"),
        entity_id=(plan_record.get("applicability") or {}).get("entity_id"),
        applicability=plan_record.get("applicability") or {},
        framework_results=framework_results,
        evidence=evidence,
    )
    return {**plan_record, "debate": d}
