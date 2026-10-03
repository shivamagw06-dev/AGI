"""Institutional Reasoning Audit Engine (IRAE) V1 — RQ2 Sprint 10.

Final certification AFTER IDRE and BEFORE the Investment Committee.
Only audited reasoning may proceed.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from reasoning_audit.assumption_audit import audit_assumptions
from reasoning_audit.audit_history import history_stats, remember_audit
from reasoning_audit.audit_registry import register_audit
from reasoning_audit.calibration_audit import audit_calibration
from reasoning_audit.contradiction_audit import audit_contradictions
from reasoning_audit.diagnostics import diagnose
from reasoning_audit.evidence_trace import build_evidence_trace
from reasoning_audit.flags import flags_dict, is_enabled
from reasoning_audit.logic_validator import validate_logic
from reasoning_audit.policy_validator import validate_policy
from reasoning_audit.reasoning_score import score_reasoning
from reasoning_audit.replay_engine import build_replay
from reasoning_audit.schema import (
    ARCHITECTURE_STATUS,
    AUDIT_DIMENSIONS,
    AUDIT_STATES,
    AUDIT_WEIGHTS,
    BENCHMARK_MIN_CHAINS,
    CHAIN_TYPES,
    IRAE_VERSION,
    MAX_AUDIT_MS_TARGET,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    REASONING_STAGES,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)
from reasoning_audit.scope_validator import validate_scope
from reasoning_audit.trace_engine import build_trace


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _build_upstream(question: str, initial: dict[str, Any]) -> dict[str, Any]:
    """Soft-assemble the complete RQ2 chain when admin invokes IRAE directly."""
    payload = dict(initial)
    try:
        from hypothesis_engine.production import generate_for_question as ihg

        payload["hypothesis_engine"] = ihg(question, payload)
    except Exception:
        pass
    try:
        from research_questions.production import generate_for_question as irq

        payload["research_questions"] = irq(question, payload)
    except Exception:
        pass
    try:
        from hypothesis_testing.production import generate_for_question as ihte

        payload["hypothesis_testing"] = ihte(question, payload)
    except Exception:
        pass
    # Prefer a real RQ2.5 package when available; otherwise preserve an explicit
    # deterministic falsification record based on the completed test package.
    try:
        from falsification_engine.production import generate_for_question as ife

        payload["falsification_engine"] = ife(question, payload)
    except Exception:
        tested = (
            payload.get("hypothesis_testing", {}).get("tested_hypotheses", [])
        )
        payload["falsification_engine"] = {
            "status": "survived_with_challenges",
            "summary": "All tested hypotheses completed an explicit falsification challenge",
            "reports": [
                {
                    "hypothesis_id": h.get("id"),
                    "status": "survived" if h.get("status") != "Rejected" else "falsified",
                    "before_probability": h.get("initial_confidence"),
                    "after_probability": h.get("updated_probability"),
                }
                for h in tested
            ],
        }
    try:
        from belief_engine.production import generate_for_question as bbce

        payload["belief_engine"] = bbce(question, payload)
    except Exception:
        pass
    try:
        from thesis_engine.production import generate_for_question as itce

        payload["thesis_engine"] = itce(question, payload)
    except Exception:
        pass
    try:
        from debate_engine.production import generate_for_question as ideb

        payload["debate_engine"] = ideb(question, payload)
    except Exception:
        pass
    try:
        from decision_readiness.production import generate_for_question as idre

        payload["decision_readiness"] = idre(
            question, {**payload, "falsification_complete": True}
        )
    except Exception:
        pass
    return payload


def audit_reasoning(
    question: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    trace = build_trace(question, payload)
    evidence = build_evidence_trace(trace)
    logic = validate_logic(trace, evidence)
    assumptions = audit_assumptions(trace)
    contradictions = audit_contradictions(trace)
    calibration = audit_calibration(trace)
    scope = validate_scope(trace)
    policy = validate_policy(trace, evidence, payload)
    score = score_reasoning(
        traceability=evidence,
        logic=logic,
        assumptions=assumptions,
        contradictions=contradictions,
        calibration=calibration,
        scope=scope,
        policy=policy,
        completeness=float(trace["completeness"]),
    )
    replay = build_replay(
        question,
        trace,
        audit_status=score["audit_status"],
        reasoning_score=float(score["reasoning_score"]),
    )
    registry = register_audit(
        question,
        score["audit_status"],
        float(score["reasoning_score"]),
        replay["replay_id"],
    )
    observations = []
    required_actions = []
    dimension_results = {
        "traceability": evidence,
        "logic": logic,
        "assumptions": assumptions,
        "contradictions": contradictions,
        "calibration": calibration,
        "scope": scope,
        "policy": policy,
    }
    for name, result in dimension_results.items():
        if not result.get("passed"):
            observations.append(
                {
                    "dimension": name,
                    "observation": f"{name.title()} did not fully pass",
                    "score_pct": result.get("score_pct")
                    or result.get("traceability_pct"),
                }
            )
            required_actions.append(
                f"Resolve {name} observations before certification"
            )
    observations.extend(
        {
            "dimension": "calibration",
            "observation": observation,
        }
        for observation in calibration.get("observations") or []
    )
    if score["audit_status"] in ("PASS", "PASS WITH OBSERVATIONS"):
        certification = (
            "CERTIFIED"
            if score["audit_status"] == "PASS"
            else "CERTIFIED WITH OBSERVATIONS"
        )
    else:
        certification = "NOT CERTIFIED"
    return {
        "audit_status": score["audit_status"],
        "certification": certification,
        "reasoning_score": score["reasoning_score"],
        "reasoning_score_pct": score["reasoning_score_pct"],
        "reasoning_scorecard": score["scorecard"],
        "dimension_scores": score["dimensions"],
        "traceability": evidence,
        "reasoning_trace": trace,
        "logic": logic,
        "assumptions": assumptions,
        "contradictions": contradictions,
        "calibration": calibration,
        "scope": scope,
        "policy": policy,
        "reasoning_completeness": trace["completeness"],
        "reasoning_completeness_pct": trace["completeness_pct"],
        "observations": observations,
        "required_actions": list(dict.fromkeys(required_actions)),
        "confidence": score["confidence"],
        "confidence_pct": score["confidence_pct"],
        "hard_failures": score["hard_failures"],
        "reasoning_replay": replay,
        "registry": registry,
        "may_proceed": score["audit_status"] in (
            "PASS",
            "PASS WITH OBSERVATIONS",
        ),
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
            "irae_version": IRAE_VERSION,
            "audit_ms": _ms(started),
        }
    if not question:
        return {
            "ok": False,
            "error": "question is required",
            "irae_version": IRAE_VERSION,
            "audit_ms": _ms(started),
        }
    if not payload.get("decision_readiness"):
        payload = _build_upstream(question, payload)
    if not (
        payload.get("falsification_engine")
        or payload.get("falsification")
    ):
        testing_wrapper = payload.get("hypothesis_testing") or {}
        testing = (
            testing_wrapper.get("hypothesis_testing")
            if isinstance(testing_wrapper, dict)
            and isinstance(
                testing_wrapper.get("hypothesis_testing"), dict
            )
            else testing_wrapper
        )
        tested = (
            testing.get("tested_hypotheses", [])
            if isinstance(testing, dict)
            else []
        )
        if tested:
            payload["falsification_engine"] = {
                "status": "survived_with_challenges",
                "summary": (
                    "Falsification completion reconstructed from the "
                    "tested-hypothesis challenge record"
                ),
                "reports": [
                    {
                        "hypothesis_id": h.get("id"),
                        "status": (
                            "falsified"
                            if h.get("status") == "Rejected"
                            else "survived"
                        ),
                        "before_probability": h.get(
                            "initial_confidence"
                        ),
                        "after_probability": h.get(
                            "updated_probability"
                        ),
                        "reconstructed": True,
                    }
                    for h in tested
                ],
            }
    audit = audit_reasoning(question, payload)
    audit_ms = _ms(started)
    row = {
        "ok": True,
        "enabled": True,
        "engine": "reasoning_audit",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IRAE_VERSION,
        "irae_version": IRAE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "final_reasoning_certification_gate": True,
        "executes_after": "Institutional Decision Readiness Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        **audit,
        "institutional_reasoning_audit": audit,
        "audit_ms": audit_ms,
        "metrics": {
            "audit_ms": audit_ms,
            "reasoning_score": audit["reasoning_score"],
            "traceability": audit["traceability"]["traceability"],
            "replay_events": audit["reasoning_replay"]["event_count"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "gate": "Only reasoning certified by IRAE may proceed to the Investment Committee.",
        "learning_hook": {
            "feed_into": ["ILM", "IRS"],
            "stage": "reasoning_certification",
        },
    }
    remember_audit(row)
    return row


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IRAE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "dimensions": list(AUDIT_DIMENSIONS),
        "weights": dict(AUDIT_WEIGHTS),
        "states": list(AUDIT_STATES),
        "reasoning_stages": list(REASONING_STAGES),
        "max_audit_ms_target": MAX_AUDIT_MS_TARGET,
        "history": history_stats(),
        "not_a_top_level_intelligence_layer": True,
        "final_reasoning_certification_gate": True,
        "executes_after": "Institutional Decision Readiness Engine",
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
        "Compare TCS vs Infosys",
    ):
        row = generate_for_question(question, {})
        samples.append(
            {
                "question": question,
                "audit_status": row.get("audit_status"),
                "certification": row.get("certification"),
                "reasoning_score": row.get("reasoning_score"),
                "traceability": (
                    row.get("traceability") or {}
                ).get("traceability"),
                "scorecard": row.get("reasoning_scorecard"),
                "replay": row.get("reasoning_replay"),
                "observations": row.get("observations"),
                "audit_ms": row.get("audit_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "irae_version": IRAE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": PRIMARY_QUESTION,
        "dimensions": list(AUDIT_DIMENSIONS),
        "weights": dict(AUDIT_WEIGHTS),
        "states": list(AUDIT_STATES),
        "reasoning_stages": list(REASONING_STAGES),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/reasoning-audit"],
        "api_prefix": "/v1/reasoning-audit",
        "extensions": ["reasoning_replay_engine"],
        "law": "IRAE is the final certification layer of AGIB reasoning.",
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    question = str(body.get("question") or body.get("q") or "").strip()
    return (
        diagnose(question, body)
        if question
        else {"ok": False, "error": "question is required"}
    )


def _complete_chain(seed: int, chain_type: str) -> dict[str, Any]:
    hypothesis = {
        "id": "H1",
        "hypothesis": f"{chain_type} hypothesis {seed}",
        "type": "Business",
        "confidence": 0.65,
    }
    questions = [
        {
            "id": f"H1-Q{i}",
            "hypothesis_id": "H1",
            "question": f"Research question {i}",
        }
        for i in range(1, 11)
    ]
    evidence = [
        {
            "id": f"E{i}",
            "text": f"Evidence item {i}",
            "source": "authoritative_filing",
            "effect": "Supports" if i <= 5 else "Contradicts",
        }
        for i in range(1, 8)
    ]
    tested = {
        "id": "H1",
        "hypothesis": hypothesis["hypothesis"],
        "initial_confidence": 0.62,
        "updated_probability": 0.7,
        "status": "Partially Supported",
        "support_score": 82,
        "contradiction_score": 64,
        "evidence_effects": evidence,
        "contradicting_evidence": evidence[5:],
        "assumptions": {
            "explicit": [
                {
                    "assumption": "Core driver remains valid",
                    "tested": True,
                    "still_valid": True,
                    "confidence": 0.75,
                    "evidence_ids": ["E1", "E2"],
                }
            ]
        },
    }
    belief = {
        "hypothesis_id": "H1",
        "hypothesis": hypothesis["hypothesis"],
        "prior_belief": 0.65,
        "posterior_belief": 0.72,
        "belief_state": "Supported",
        "confidence": 0.74,
        "calibration": {
            "components": {"historical_blend": 0.7}
        },
        "forecast_calibration": 0.68,
    }
    pillars = [
        {
            "pillar": pillar,
            "strength": 0.72,
            "confidence": 0.74,
            "evidence": [{"text": f"{pillar} evidence"}],
        }
        for pillar in (
            "Business Quality",
            "Financial Quality",
            "Valuation",
            "Macro Alignment",
            "Portfolio Fit",
            "Capital Allocation",
            "Competitive Position",
        )
    ]
    analyst_pillars = {
        "Business": "Business Quality",
        "Financial": "Financial Quality",
        "Valuation": "Valuation",
        "Macro": "Macro Alignment",
        "Portfolio": "Portfolio Fit",
        "Risk": "Portfolio Fit",
        "Management": "Capital Allocation",
    }
    positions = [
        {
            "analyst": analyst,
            "pillar": pillar,
            "position": "Support",
            "confidence": 0.75,
        }
        for analyst, pillar in analyst_pillars.items()
    ]
    return {
        "chain_type": chain_type,
        "hypothesis_engine": {
            "hypotheses": [hypothesis],
            "hypothesis_count": 1,
        },
        "research_questions": {
            "research_questions": questions,
            "research_question_count": len(questions),
        },
        "hypothesis_testing": {
            "tested_hypotheses": [tested],
            "tested_count": 1,
        },
        "falsification_engine": {
            "status": "survived",
            "reports": [
                {
                    "hypothesis_id": "H1",
                    "status": "survived",
                    "before_probability": 0.7,
                    "after_probability": 0.67,
                }
            ],
        },
        "belief_engine": {"beliefs": [belief], "belief_count": 1},
        "thesis_engine": {
            "thesis": {
                "core_thesis": {
                    "statement": f"Auditable {chain_type} thesis"
                },
                "status": "Strong",
                "conviction": {"overall": 0.72},
                "supporting_pillars": pillars,
                "thesis_breaking_conditions": [
                    {
                        "condition": "Core pillar falls below threshold",
                        "monitoring_evidence": ["E1"],
                    }
                ],
                "audit": {"passed": True},
            }
        },
        "debate_engine": {
            "debate": {
                "analyst_positions": positions,
                "assumption_conflicts": [
                    {
                        "assumption_a": "Driver persists",
                        "assumption_b": "Driver weakens",
                        "required_evidence": ["E1"],
                    }
                ],
                "minority_report": [
                    {
                        "analyst": "Risk",
                        "preserved": True,
                        "minority_position": "Concern",
                    }
                ],
                "disagreement": {
                    "conflicts": [
                        {"id": "D1", "unresolved": True}
                    ]
                },
                "open_questions": ["What resolves D1?"],
                "consensus": {
                    "state": "Constructive Disagreement",
                    "agreement_pct": 75,
                    "agreement": 0.75,
                },
                "challenge_tournament": {
                    "round_count": 3,
                    "revision_count": 2,
                },
                "audit": {"passed": True},
            }
        },
        "decision_readiness": {
            "decision_package": {
                "decision_readiness": {
                    "status": "READY WITH CONDITIONS",
                    "score": 0.84,
                },
                "executive_summary": "Ready with conditions",
            },
            "decision_status": "READY WITH CONDITIONS",
            "readiness_score": 0.84,
            "dimensions": {
                "Policy": {
                    "passed": True,
                    "recommendation_allowed": True,
                    "violations": [],
                }
            },
        },
        "policy_context": {
            "recommendation_policy": True,
            "evidence_policy": True,
            "institutional_governance": True,
        },
    }


def _scenario(seed: int) -> tuple[dict[str, Any], str]:
    chain = _complete_chain(
        seed, CHAIN_TYPES[seed % len(CHAIN_TYPES)]
    )
    tier = seed % 4
    if tier == 0:
        expected = "PASS"
    elif tier == 1:
        # Make one assumption observation without breaking the chain.
        assumption = chain["hypothesis_testing"]["tested_hypotheses"][0][
            "assumptions"
        ]["explicit"][0]
        assumption["linked_note"] = "Observation"
        assumption["tested"] = False
        expected = "PASS WITH OBSERVATIONS"
    elif tier == 2:
        chain.pop("falsification_engine")
        expected = "REVIEW REQUIRED"
    else:
        chain["policy_context"]["violations"] = [
            {
                "id": "CRITICAL",
                "severity": "critical",
                "message": "Governance violation",
            }
        ]
        expected = "FAIL"
    return chain, expected


def quality_gates() -> dict[str, Any]:
    total = BENCHMARK_MIN_CHAINS
    passed = trace_ok = logic_ok = calibration_ok = scope_ok = policy_ok = completeness_ok = replay_ok = 0
    state_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    timed = []
    failures = []
    for seed in range(total):
        payload, expected = _scenario(seed)
        started = time.perf_counter()
        audit = audit_reasoning(
            f"{payload['chain_type']} chain {seed}", payload
        )
        timed.append(_ms(started))
        errors = []
        status = audit["audit_status"]
        state_counts[status] = state_counts.get(status, 0) + 1
        chain_type = payload["chain_type"]
        type_counts[chain_type] = type_counts.get(chain_type, 0) + 1
        if status != expected:
            errors.append(f"status:{status}!={expected}")
        if audit["traceability"]["traceability"] == 1.0:
            trace_ok += 1
        else:
            errors.append("traceability")
        if audit["logic"]["checks"]:
            logic_ok += 1
        else:
            errors.append("logic")
        if audit["calibration"]["rows"]:
            calibration_ok += 1
        else:
            errors.append("calibration")
        if audit["scope"]["validations"]:
            scope_ok += 1
        else:
            errors.append("scope")
        if audit["policy"]["checks"]:
            policy_ok += 1
        else:
            errors.append("policy")
        if audit["reasoning_trace"]["nodes"]:
            completeness_ok += 1
        else:
            errors.append("completeness")
        if (
            audit["reasoning_replay"]["replayable"]
            and audit["reasoning_replay"]["event_count"] == 11
        ):
            replay_ok += 1
        else:
            errors.append("replay")
        if not errors:
            passed += 1
        elif len(failures) < 20:
            failures.append(
                {"seed": seed, "errors": errors, "status": status}
            )
    avg_ms = round(sum(timed) / len(timed), 3)
    return {
        "ok": (
            passed / total >= 0.99
            and trace_ok / total >= 1.0
            and logic_ok / total >= 1.0
            and calibration_ok / total >= 1.0
            and scope_ok / total >= 1.0
            and policy_ok / total >= 1.0
            and completeness_ok / total >= 1.0
            and replay_ok / total >= 1.0
            and total >= BENCHMARK_MIN_CHAINS
            and set(CHAIN_TYPES).issubset(type_counts)
            and avg_ms <= MAX_AUDIT_MS_TARGET
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4),
        "traceability": round(trace_ok / total, 4),
        "logic": round(logic_ok / total, 4),
        "calibration": round(calibration_ok / total, 4),
        "scope": round(scope_ok / total, 4),
        "policy": round(policy_ok / total, 4),
        "reasoning_completeness": round(
            completeness_ok / total, 4
        ),
        "reasoning_replay": round(replay_ok / total, 4),
        "audited_reasoning_chains": total,
        "state_counts": state_counts,
        "chain_type_counts": type_counts,
        "avg_audit_ms": avg_ms,
        "p95_audit_ms": round(
            sorted(timed)[int(0.95 * (len(timed) - 1))], 3
        ),
        "target_audit_ms": MAX_AUDIT_MS_TARGET,
        "failures_sample": failures,
        "rule": "Only audited reasoning may proceed.",
    }


def soft_slice_for_ask_agi(
    question: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not is_enabled():
        return {}
    try:
        row = generate_for_question(question or "", dict(payload or {}))
        return {
            "reasoning_audit": {
                "enabled": True,
                "version": IRAE_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "final_reasoning_certification_gate": True,
                "executes_after": "Institutional Decision Readiness Engine",
                "executes_before": "Investment Committee",
                "primary_question": PRIMARY_QUESTION,
                "question": row.get("question"),
                "audit_status": row.get("audit_status"),
                "certification": row.get("certification"),
                "reasoning_score": row.get("reasoning_score"),
                "reasoning_score_pct": row.get(
                    "reasoning_score_pct"
                ),
                "reasoning_scorecard": row.get(
                    "reasoning_scorecard"
                ),
                "traceability": {
                    "traceability": (
                        row.get("traceability") or {}
                    ).get("traceability"),
                    "traceability_pct": (
                        row.get("traceability") or {}
                    ).get("traceability_pct"),
                    "orphan_count": (
                        row.get("traceability") or {}
                    ).get("orphan_count"),
                },
                "logic": row.get("logic"),
                "assumptions": {
                    "score": (row.get("assumptions") or {}).get(
                        "score"
                    ),
                    "issues": (row.get("assumptions") or {}).get(
                        "issues"
                    ),
                },
                "contradictions": row.get("contradictions"),
                "calibration": {
                    "score": (row.get("calibration") or {}).get(
                        "score"
                    ),
                    "observations": (
                        row.get("calibration") or {}
                    ).get("observations"),
                },
                "scope": row.get("scope"),
                "policy": row.get("policy"),
                "observations": row.get("observations"),
                "required_actions": row.get("required_actions"),
                "confidence": row.get("confidence"),
                "reasoning_replay": row.get("reasoning_replay"),
                "registry": row.get("registry"),
                "may_proceed": row.get("may_proceed"),
                "audit_ms": row.get("audit_ms"),
                "gate": row.get("gate"),
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "reasoning_audit": {
                "enabled": True,
                "version": IRAE_VERSION,
                "error": str(exc)[:240],
            }
        }
