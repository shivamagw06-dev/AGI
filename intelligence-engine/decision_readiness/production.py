"""Institutional Decision Readiness Engine (IDRE) V1 — RQ2 Sprint 9.

Final institutional quality gate AFTER IDEB and BEFORE the Investment Committee.
Not a top-level intelligence layer.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from decision_readiness.audit import audit_package
from decision_readiness.conflict_gate import evaluate_debate
from decision_readiness.decision_package import build_decision_package
from decision_readiness.diagnostics import diagnose
from decision_readiness.evidence_gate import evaluate_evidence
from decision_readiness.flags import flags_dict, is_enabled
from decision_readiness.monitoring_gate import evaluate_monitoring
from decision_readiness.portfolio_gate import evaluate_portfolio
from decision_readiness.readiness_engine import aggregate_readiness
from decision_readiness.recommendation_gate import evaluate_policy
from decision_readiness.schema import (
    ARCHITECTURE_STATUS,
    BENCHMARK_MIN_SCENARIOS,
    IDRE_VERSION,
    MAX_READINESS_MS_TARGET,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    READINESS_DIMENSIONS,
    READINESS_STATES,
    READINESS_WEIGHTS,
    RESEARCH_TYPES,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)
from decision_readiness.thesis_gate import evaluate_reasoning
from decision_readiness.uncertainty_gate import evaluate_uncertainty


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_thesis(payload: dict[str, Any]) -> dict[str, Any]:
    wrapper = _safe_dict(payload.get("thesis_engine"))
    body = _safe_dict(wrapper.get("thesis_engine")) or wrapper
    thesis = _safe_dict(
        body.get("thesis")
        or body.get("institutional_investment_thesis")
        or payload.get("thesis")
    )
    if not thesis and body.get("core_thesis"):
        thesis = body
    return thesis


def _extract_debate(payload: dict[str, Any]) -> dict[str, Any]:
    wrapper = _safe_dict(payload.get("debate_engine"))
    body = _safe_dict(wrapper.get("debate_engine")) or wrapper
    debate = _safe_dict(
        body.get("debate")
        or body.get("institutional_debate_package")
        or payload.get("debate")
    )
    if not debate and body.get("consensus"):
        debate = body
    return debate


def _extract_belief_package(payload: dict[str, Any]) -> dict[str, Any]:
    wrapper = _safe_dict(payload.get("belief_engine"))
    body = _safe_dict(wrapper.get("belief_engine")) or wrapper
    return _safe_dict(body.get("institutional_belief_package")) or body


def _try_upstream(
    question: str, payload: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        from thesis_engine.production import generate_for_question as build_thesis

        thesis_row = build_thesis(question, payload)
        thesis = _safe_dict(thesis_row.get("thesis"))
    except Exception:
        thesis = {}
    try:
        from debate_engine.production import build_debate

        debate = build_debate(thesis) if thesis else {}
    except Exception:
        debate = {}
    return thesis, debate


def build_readiness(
    *,
    question: str,
    thesis: dict[str, Any],
    debate: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    evidence_gate = evaluate_evidence(thesis, debate, payload)
    reasoning_gate = evaluate_reasoning(thesis, payload)
    debate_gate = evaluate_debate(debate)
    portfolio_gate = evaluate_portfolio(thesis, payload)
    monitoring_gate = evaluate_monitoring(thesis)
    policy_gate = evaluate_policy(thesis, debate, payload)
    confidence_gate = evaluate_uncertainty(
        thesis, debate, _extract_belief_package(payload)
    )

    readiness = aggregate_readiness(
        evidence=evidence_gate,
        reasoning=reasoning_gate,
        debate=debate_gate,
        portfolio=portfolio_gate,
        monitoring=monitoring_gate,
        policy=policy_gate,
        confidence=confidence_gate,
    )
    package = build_decision_package(
        question=question,
        thesis=thesis,
        debate=debate,
        readiness=readiness,
    )
    audit = audit_package(readiness, package)
    return {
        **readiness,
        "decision_package": package,
        "audit": audit,
        "missing_evidence": package["missing_evidence"],
        "open_questions": package["open_questions"],
        "remaining_conflicts": package["remaining_conflicts"],
        "portfolio_constraints": package["portfolio_constraints"],
        "monitoring_plan": package["monitoring"],
        "decision_conditions": package["conditions"],
        "required_follow_up": package["required_follow_up"],
        "capital_allocation_readiness": package[
            "capital_allocation_readiness"
        ],
        "capital_allocation_readiness_pct": package[
            "capital_allocation_readiness_pct"
        ],
        "capital_state": package["capital_state"],
    }


def generate_for_question(
    question: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(payload or {})
    question = str(
        question or payload.get("question") or payload.get("q") or ""
    ).strip()
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "idre_version": IDRE_VERSION,
            "readiness_ms": _ms(started),
        }
    if not question:
        return {
            "ok": False,
            "error": "question is required",
            "idre_version": IDRE_VERSION,
            "readiness_ms": _ms(started),
        }

    thesis = _extract_thesis(payload)
    debate = _extract_debate(payload)
    upstream_imported = False
    if not thesis or not debate:
        upstream_thesis, upstream_debate = _try_upstream(question, payload)
        thesis = thesis or upstream_thesis
        debate = debate or upstream_debate
        upstream_imported = bool(upstream_thesis and upstream_debate)
    if not thesis or not debate:
        # Upstream packages exist on this stacked branch; this is defensive only.
        return {
            "ok": False,
            "error": "Investment thesis and institutional debate are required",
            "idre_version": IDRE_VERSION,
            "readiness_ms": _ms(started),
        }

    readiness = build_readiness(
        question=question,
        thesis=thesis,
        debate=debate,
        payload=payload,
    )
    readiness_ms = _ms(started)
    return {
        "ok": True,
        "enabled": True,
        "engine": "decision_readiness",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IDRE_VERSION,
        "idre_version": IDRE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "final_pre_committee_quality_gate": True,
        "executes_after": "Institutional Debate Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        **readiness,
        "institutional_decision_package": readiness["decision_package"],
        "upstream_soft_imported": upstream_imported,
        "readiness_ms": readiness_ms,
        "metrics": {
            "readiness_ms": readiness_ms,
            "readiness_score": readiness["readiness_score"],
            "capital_allocation_readiness": readiness[
                "capital_allocation_readiness"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "gate": (
            "The Investment Committee receives a structured decision package, "
            "never a raw thesis."
        ),
    }


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IDRE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "dimensions": list(READINESS_DIMENSIONS),
        "weights": dict(READINESS_WEIGHTS),
        "states": list(READINESS_STATES),
        "max_readiness_ms_target": MAX_READINESS_MS_TARGET,
        "not_a_top_level_intelligence_layer": True,
        "final_pre_committee_quality_gate": True,
        "executes_after": "Institutional Debate Engine",
        "executes_before": "Investment Committee",
        "law": PRIMARY_QUESTION,
    }


def constitution() -> dict[str, Any]:
    return {
        "enabled": is_enabled(),
        **constitution_dict(),
        "flags": flags_dict(),
    }


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    question = str(
        body.get("question") or body.get("q") or body.get("text") or ""
    ).strip()
    return generate_for_question(question, body)


def dashboard() -> dict[str, Any]:
    samples = []
    for question in (
        "Should I buy HDFC Bank?",
        "Is Nifty IT expensive versus history?",
        "Build a ₹500,000 portfolio",
    ):
        row = generate_for_question(
            question,
            {
                "falsification_complete": True,
                "evidence_metrics": {
                    "coverage": 0.92,
                    "authority": 0.94,
                    "freshness": 0.9,
                    "independence": 0.88,
                },
            },
        )
        samples.append(
            {
                "question": question,
                "decision_status": row.get("decision_status"),
                "readiness_score": row.get("readiness_score"),
                "heat_map": row.get("decision_heat_map"),
                "capital_allocation_readiness": row.get(
                    "capital_allocation_readiness"
                ),
                "decision_package": row.get("decision_package"),
                "readiness_ms": row.get("readiness_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "idre_version": IDRE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": PRIMARY_QUESTION,
        "dimensions": list(READINESS_DIMENSIONS),
        "weights": dict(READINESS_WEIGHTS),
        "states": list(READINESS_STATES),
        "research_types": list(RESEARCH_TYPES),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/decision-readiness"],
        "api_prefix": "/v1/decision-readiness",
        "extensions": [
            "decision_heat_map",
            "objective_go_no_go_conditions",
            "capital_allocation_readiness",
        ],
        "law": "IDRE is the final institutional quality gate before Committee deliberation.",
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    question = str(body.get("question") or body.get("q") or "").strip()
    return (
        diagnose(question, body)
        if question
        else {"ok": False, "error": "question is required"}
    )


def _scenario(seed: int) -> tuple[str, dict[str, Any], str]:
    tier = seed % 4
    research_type = RESEARCH_TYPES[seed % len(RESEARCH_TYPES)]
    from debate_engine.production import _fallback_thesis, build_debate

    thesis = _fallback_thesis(f"Scenario {seed}")
    debate = build_debate(thesis)
    base = {
        "thesis": thesis,
        "debate": debate,
        "hypothesis_testing": {"tested": True},
        "belief_engine": {"beliefs": [{"confidence": 0.8}]},
        "falsification_complete": True,
        "research_type": research_type,
        "policy_context": {},
        "portfolio_context": {},
    }
    if tier == 0:  # READY
        base["evidence_metrics"] = {
            "coverage": 0.98,
            "authority": 0.97,
            "freshness": 0.95,
            "independence": 0.95,
            "contradiction_coverage": 0.98,
        }
        debate["consensus"].update(
            {
                "agreement": 0.9,
                "confidence": 0.9,
                "evidence_sufficiency": 0.95,
                "vote_ready": True,
            }
        )
        debate["disagreement"]["material_count"] = 0
        base["portfolio_context"] = {
            "position_suitability": 0.9,
            "sector_concentration": 0.15,
            "factor_exposure": 0.15,
            "risk_budget_used": 0.55,
            "liquidity": 0.95,
            "diversification": 0.85,
        }
        expected = "READY"
    elif tier == 1:  # READY WITH CONDITIONS
        base["evidence_metrics"] = {
            "coverage": 0.88,
            "authority": 0.9,
            "freshness": 0.86,
            "independence": 0.84,
            "contradiction_coverage": 0.9,
        }
        debate["consensus"].update(
            {
                "agreement": 0.72,
                "confidence": 0.74,
                "evidence_sufficiency": 0.8,
                "vote_ready": True,
            }
        )
        debate["disagreement"]["material_count"] = 1
        expected = "READY WITH CONDITIONS"
    elif tier == 2:  # RESEARCH REQUIRED
        base["evidence_metrics"] = {
            "coverage": 0.68,
            "authority": 0.72,
            "freshness": 0.65,
            "independence": 0.62,
            "contradiction_coverage": 0.7,
        }
        debate["consensus"].update(
            {
                "agreement": 0.5,
                "confidence": 0.55,
                "evidence_sufficiency": 0.58,
                "vote_ready": False,
            }
        )
        debate["disagreement"]["material_count"] = 4
        expected = "RESEARCH REQUIRED"
    else:  # NOT READY
        base["evidence_metrics"] = {
            "coverage": 0.35,
            "authority": 0.5,
            "freshness": 0.4,
            "independence": 0.4,
            "contradiction_coverage": 0.4,
        }
        base["policy_context"] = {
            "violations": [
                {
                    "id": "POL-CRIT",
                    "severity": "critical",
                    "message": "Recommendation policy violation",
                }
            ]
        }
        expected = "NOT READY"
    return research_type, base, expected


def quality_gates() -> dict[str, Any]:
    total = BENCHMARK_MIN_SCENARIOS
    passed = classification_ok = evidence_ok = monitoring_ok = conflict_ok = package_ok = 0
    heat_ok = conditions_ok = capital_ok = 0
    type_counts: dict[str, int] = {}
    state_counts: dict[str, int] = {}
    timed = []
    failures = []
    for seed in range(total):
        research_type, payload, expected = _scenario(seed)
        started = time.perf_counter()
        readiness = build_readiness(
            question=f"{research_type} scenario {seed}",
            thesis=payload["thesis"],
            debate=payload["debate"],
            payload=payload,
        )
        timed.append(_ms(started))
        errors = []
        status = readiness["decision_status"]
        type_counts[research_type] = type_counts.get(research_type, 0) + 1
        state_counts[status] = state_counts.get(status, 0) + 1
        if status == expected:
            classification_ok += 1
        else:
            errors.append(f"classification:{status}!={expected}")
        evidence = readiness["dimensions"]["Evidence"]
        if evidence.get("checks") and evidence.get("coverage_pct") is not None:
            evidence_ok += 1
        else:
            errors.append("evidence")
        if readiness["monitoring_plan"].get("active_triggers") and len(
            readiness["decision_conditions"]
        ) >= 3:
            monitoring_ok += 1
        else:
            errors.append("monitoring")
        if readiness["remaining_conflicts"] is not None and readiness[
            "dimensions"
        ]["Debate"].get("minority_reviewed"):
            conflict_ok += 1
        else:
            errors.append("conflict")
        package = readiness["decision_package"]
        if (
            package["decision_readiness"]["status"] == status
            and package.get("executive_summary")
        ):
            package_ok += 1
        else:
            errors.append("package")
        if len(readiness["decision_heat_map"]) == 7:
            heat_ok += 1
        else:
            errors.append("heat_map")
        if all(
            condition.get("result") in ("GO", "NO-GO")
            for condition in readiness["decision_conditions"]
        ):
            conditions_ok += 1
        else:
            errors.append("conditions")
        if readiness["capital_allocation_readiness"] is not None:
            capital_ok += 1
        else:
            errors.append("capital")
        if not errors:
            passed += 1
        elif len(failures) < 20:
            failures.append(
                {
                    "seed": seed,
                    "research_type": research_type,
                    "errors": errors,
                }
            )
    avg_ms = round(sum(timed) / len(timed), 3)
    return {
        "ok": (
            passed / total >= 0.99
            and classification_ok / total >= 0.99
            and evidence_ok / total >= 1.0
            and monitoring_ok / total >= 1.0
            and conflict_ok / total >= 1.0
            and package_ok / total >= 1.0
            and heat_ok / total >= 1.0
            and conditions_ok / total >= 1.0
            and capital_ok / total >= 1.0
            and total >= BENCHMARK_MIN_SCENARIOS
            and set(RESEARCH_TYPES).issubset(type_counts)
            and avg_ms <= MAX_READINESS_MS_TARGET
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4),
        "readiness_classification": round(classification_ok / total, 4),
        "evidence_completeness": round(evidence_ok / total, 4),
        "monitoring_quality": round(monitoring_ok / total, 4),
        "conflict_resolution": round(conflict_ok / total, 4),
        "decision_package_consistency": round(package_ok / total, 4),
        "decision_heat_map": round(heat_ok / total, 4),
        "decision_conditions": round(conditions_ok / total, 4),
        "capital_allocation_readiness": round(capital_ok / total, 4),
        "decision_scenarios": total,
        "research_type_counts": type_counts,
        "state_counts": state_counts,
        "avg_readiness_ms": avg_ms,
        "p95_readiness_ms": round(
            sorted(timed)[int(0.95 * (len(timed) - 1))], 3
        ),
        "target_readiness_ms": MAX_READINESS_MS_TARGET,
        "failures_sample": failures,
        "rule": "The Committee receives a decision package, never a raw thesis.",
    }


def soft_slice_for_ask_agi(
    question: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not is_enabled():
        return {}
    try:
        row = generate_for_question(question or "", dict(payload or {}))
        if not row.get("ok"):
            return {
                "decision_readiness": {
                    "enabled": True,
                    "version": IDRE_VERSION,
                    "error": row.get("error"),
                }
            }
        package = row["decision_package"]
        return {
            "decision_readiness": {
                "enabled": True,
                "version": IDRE_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "final_pre_committee_quality_gate": True,
                "executes_after": "Institutional Debate Engine",
                "executes_before": "Investment Committee",
                "primary_question": PRIMARY_QUESTION,
                "question": row.get("question"),
                "decision_status": row.get("decision_status"),
                "readiness_score": row.get("readiness_score"),
                "readiness_score_pct": row.get("readiness_score_pct"),
                "decision_heat_map": row.get("decision_heat_map"),
                "strengths": row.get("strengths"),
                "weaknesses": row.get("weaknesses"),
                "missing_evidence": row.get("missing_evidence"),
                "open_questions": row.get("open_questions"),
                "remaining_conflicts": row.get("remaining_conflicts"),
                "portfolio_constraints": row.get("portfolio_constraints"),
                "monitoring_plan": row.get("monitoring_plan"),
                "decision_conditions": row.get("decision_conditions"),
                "required_follow_up": row.get("required_follow_up"),
                "confidence": row.get("confidence"),
                "capital_allocation_readiness": row.get(
                    "capital_allocation_readiness"
                ),
                "capital_allocation_readiness_pct": row.get(
                    "capital_allocation_readiness_pct"
                ),
                "capital_state": row.get("capital_state"),
                "executive_summary": package.get("executive_summary"),
                "committee_handoff": package.get("committee_handoff"),
                "readiness_ms": row.get("readiness_ms"),
                "gate": row.get("gate"),
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "decision_readiness": {
                "enabled": True,
                "version": IDRE_VERSION,
                "error": str(exc)[:240],
            }
        }
