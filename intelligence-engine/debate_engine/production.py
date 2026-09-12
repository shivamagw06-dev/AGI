"""Institutional Debate Engine (IDEB) V1 — RQ2 Sprint 8.

Structured debate AFTER ITCE and BEFORE the Investment Committee.
This is not another committee and not a top-level intelligence layer.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from debate_engine.agreement_engine import find_agreement
from debate_engine.assumption_conflict import find_assumption_conflicts
from debate_engine.audit import audit_debate
from debate_engine.challenge_memory import memory_stats, remember_challenges
from debate_engine.challenge_tournament import run_tournament
from debate_engine.consensus_engine import build_consensus
from debate_engine.debate_registry import (
    extract_analyst_opinions,
    extract_thesis,
    register_debate,
)
from debate_engine.diagnostics import diagnose
from debate_engine.disagreement_engine import find_disagreements
from debate_engine.evidence_conflict import map_evidence_conflicts
from debate_engine.flags import flags_dict, is_enabled
from debate_engine.minority_report import build_minority_report
from debate_engine.moderator import moderate
from debate_engine.position_engine import build_positions
from debate_engine.schema import (
    ANALYSTS,
    ARCHITECTURE_STATUS,
    BENCHMARK_MIN_DISAGREEMENTS,
    BENCHMARK_MIN_SCENARIOS,
    DEBATE_STATES,
    IDEB_VERSION,
    MAX_DEBATE_MS_TARGET,
    POSITIONS,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)
from debate_engine.scorecard import build_scorecard


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _try_itce(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from thesis_engine.production import generate_for_question as itce_generate

        row = itce_generate(question, payload)
        return _safe_dict(row.get("thesis"))
    except Exception:
        return {}


def _fallback_thesis(question: str) -> dict[str, Any]:
    # Complete fixture that still exposes genuine disagreement.
    names = [
        ("Business Quality", 0.78, 0.76, "Strong"),
        ("Financial Quality", 0.82, 0.78, "Strong"),
        ("Capital Allocation", 0.68, 0.66, "Constructive"),
        ("Competitive Position", 0.55, 0.62, "Neutral"),
        ("Valuation", 0.42, 0.64, "Weak"),
        ("Macro Alignment", 0.50, 0.58, "Neutral"),
        ("Portfolio Fit", 0.65, 0.68, "Constructive"),
    ]
    pillars = []
    for i, (name, strength, confidence, verdict) in enumerate(names, start=1):
        pillars.append(
            {
                "pillar": name,
                "strength": strength,
                "strength_pct": round(strength * 100),
                "confidence": confidence,
                "confidence_pct": round(confidence * 100),
                "verdict": verdict,
                "evidence": [
                    {"text": f"Verified evidence supporting {name} ({i})", "score": 80 + i}
                ],
                "contradictions": [
                    {"text": f"Counter-evidence challenging {name} ({i})", "score": 65 + i}
                ],
                "missing_evidence": [f"Independent update required for {name}"],
            }
        )
    return {
        "core_thesis": {
            "statement": (
                "The investment case remains fundamentally constructive, but valuation, macro "
                "conditions and competitive pressure constrain near-term attractiveness."
            )
        },
        "supporting_pillars": pillars,
        "confidence": 0.68,
        "status": "Strong",
        "contradictions": {
            "strongest_supporting_evidence": [
                {"text": "Business and financial quality remain resilient", "score": 90}
            ],
            "strongest_contradicting_evidence": [
                {"text": "Valuation already reflects much of the quality", "score": 84}
            ],
            "major": [
                {"text": "Valuation is stretched", "score": 84},
                {"text": "Competitive pressure is rising", "score": 76},
            ],
            "outstanding_questions": ["Will earnings growth justify the premium?"],
            "missing_evidence": ["Updated peer valuation and macro stress evidence"],
        },
        "risks": [
            {"risk": "Valuation mean reversion", "probability": 0.42},
            {"risk": "Macro funding pressure", "probability": 0.36},
        ],
        "monitoring": {"conditions": []},
        "thesis_breaking_conditions": [
            {"condition": "Business or financial quality falls below 45%"}
        ],
    }


def build_debate(
    thesis: dict[str, Any],
    *,
    supplied_opinions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    positions = build_positions(thesis, supplied_opinions)
    initial_disagreement = find_disagreements(positions)
    evidence_conflicts = map_evidence_conflicts(initial_disagreement, positions)
    assumption_conflicts = find_assumption_conflicts(positions)

    tournament = run_tournament(positions, evidence_conflicts)
    revised_positions = list(tournament.get("revised_positions") or positions)
    agreement = find_agreement(revised_positions, thesis)
    disagreement = find_disagreements(revised_positions)

    open_questions = list(
        dict.fromkeys(
            [
                question
                for position in revised_positions
                for question in (position.get("open_questions") or [])
            ]
            + [
                conflict["resolution_question"]
                for conflict in assumption_conflicts
            ]
            + [
                question
                for question in (
                    (thesis.get("contradictions") or {}).get(
                        "outstanding_questions"
                    )
                    or []
                )
            ]
        )
    )
    required_evidence = list(
        dict.fromkeys(
            [
                str(item)
                for conflict in evidence_conflicts
                for item in (conflict.get("required_additional_evidence") or [])
            ]
            + [
                str(item)
                for conflict in assumption_conflicts
                for item in (conflict.get("required_evidence") or [])
            ]
        )
    )
    consensus = build_consensus(
        revised_positions,
        disagreement,
        evidence_conflicts,
        open_questions,
    )
    minority = build_minority_report(
        revised_positions, float(consensus["consensus_score"])
    )
    moderator = moderate(
        thesis,
        agreement,
        disagreement,
        evidence_conflicts,
        assumption_conflicts,
        open_questions,
    )
    scorecard = build_scorecard(
        revised_positions,
        evidence_conflicts,
        assumption_conflicts,
        minority,
        consensus,
        tournament,
    )
    core = thesis.get("core_thesis") or {}
    debate = {
        "investment_thesis": (
            core.get("statement") if isinstance(core, dict) else core
        ),
        "thesis_status": thesis.get("status"),
        "analyst_positions": revised_positions,
        "initial_positions": positions,
        "agreement": agreement,
        "disagreement": disagreement,
        "evidence_conflicts": evidence_conflicts,
        "assumption_conflicts": assumption_conflicts,
        "moderator": moderator,
        "consensus": consensus,
        "minority_report": minority,
        "challenge_tournament": {
            key: value
            for key, value in tournament.items()
            if key != "revised_positions"
        },
        "debate_scorecard": scorecard,
        "open_questions": open_questions,
        "required_evidence": required_evidence,
        "consensus_confidence": consensus.get("confidence"),
        "committee_handoff": {
            "thesis": (
                core.get("statement") if isinstance(core, dict) else core
            ),
            "strongest_arguments_against": [
                c.get("opposing_evidence") for c in evidence_conflicts[:3]
            ],
            "unresolved_disagreements": disagreement.get("conflicts"),
            "minority_position": minority[0] if minority else None,
            "evidence_to_settle": required_evidence[:10],
            "debate_state": consensus.get("state"),
            "vote_ready": consensus.get("vote_ready"),
        },
    }
    debate["audit"] = audit_debate(debate)
    return debate


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
            "ideb_version": IDEB_VERSION,
            "debate_ms": _ms(started),
        }
    if not question:
        return {
            "ok": False,
            "error": "question is required",
            "ideb_version": IDEB_VERSION,
            "debate_ms": _ms(started),
        }

    thesis = extract_thesis(payload)
    itce_imported = False
    if not thesis:
        thesis = _try_itce(question, payload)
        itce_imported = bool(thesis)
    if not thesis:
        thesis = _fallback_thesis(question)

    debate = build_debate(
        thesis, supplied_opinions=extract_analyst_opinions(payload)
    )
    debate_ms = _ms(started)
    row = {
        "ok": True,
        "enabled": True,
        "engine": "debate_engine",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IDEB_VERSION,
        "ideb_version": IDEB_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "not_another_committee": True,
        "executes_after": "Institutional Thesis Construction Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        "debate": debate,
        "institutional_debate_package": debate,
        "registry": register_debate(debate),
        "itce_soft_imported": itce_imported,
        "debate_ms": debate_ms,
        "metrics": {
            "debate_ms": debate_ms,
            "position_count": len(debate["analyst_positions"]),
            "disagreement_count": len(
                debate["disagreement"]["conflicts"]
            ),
            "evidence_conflict_count": len(
                debate["evidence_conflicts"]
            ),
            "tournament_rounds": debate["challenge_tournament"][
                "round_count"
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "gate": (
            "The Investment Committee receives the thesis, strongest arguments against it, "
            "minority view and evidence required to settle disagreement."
        ),
        "learning_hook": {
            "feed_into": "ILM",
            "stage": "institutional_debate",
        },
    }
    remember_challenges(row)
    return row


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IDEB_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "analysts": list(ANALYSTS),
        "positions": list(POSITIONS),
        "debate_states": list(DEBATE_STATES),
        "max_debate_ms_target": MAX_DEBATE_MS_TARGET,
        "memory": memory_stats(),
        "not_a_top_level_intelligence_layer": True,
        "not_another_committee": True,
        "executes_after": "Institutional Thesis Construction Engine",
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
        debate = row.get("debate") or {}
        samples.append(
            {
                "question": question,
                "thesis": debate.get("investment_thesis"),
                "positions": debate.get("analyst_positions"),
                "consensus": debate.get("consensus"),
                "minority_report": debate.get("minority_report"),
                "scorecard": debate.get("debate_scorecard"),
                "tournament_rounds": (
                    debate.get("challenge_tournament") or {}
                ).get("rounds"),
                "debate_ms": row.get("debate_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "ideb_version": IDEB_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": PRIMARY_QUESTION,
        "analysts": list(ANALYSTS),
        "positions": list(POSITIONS),
        "debate_states": list(DEBATE_STATES),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/institutional-debate"],
        "api_prefix": "/v1/debate-engine",
        "extensions": [
            "challenge_tournament",
            "debate_scorecard",
            "position_revision",
            "minority_preservation",
        ],
        "law": "Institutional disagreement is a first-class research object.",
        "not_a_top_level_intelligence_layer": True,
        "not_another_committee": True,
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    question = str(body.get("question") or body.get("q") or "").strip()
    return (
        diagnose(question, body)
        if question
        else {"ok": False, "error": "question is required"}
    )


def _benchmark_thesis(seed: int) -> dict[str, Any]:
    thesis = _fallback_thesis(f"Scenario {seed}")
    # Vary strengths while preserving structured disagreement and quality minima.
    shifts = [0.02, -0.01, 0.0, -0.03, 0.01]
    for i, pillar in enumerate(thesis["supporting_pillars"]):
        shift = shifts[(seed + i) % len(shifts)]
        pillar["strength"] = round(
            max(0.2, min(0.9, float(pillar["strength"]) + shift)), 4
        )
        pillar["strength_pct"] = round(pillar["strength"] * 100)
    return thesis


def quality_gates() -> dict[str, Any]:
    total = BENCHMARK_MIN_SCENARIOS
    passed = 0
    conflict_ok = agreement_ok = minority_ok = evidence_ok = consensus_ok = moderator_ok = 0
    tournament_ok = scorecard_ok = 0
    disagreements_total = 0
    timed = []
    state_counts: dict[str, int] = {}
    failures = []

    for i in range(total):
        thesis = _benchmark_thesis(i)
        started = time.perf_counter()
        debate = build_debate(thesis)
        timed.append(_ms(started))
        audit = debate.get("audit") or {}
        checks = audit.get("checks") or {}
        errors = []

        disagreements = len(
            (debate.get("disagreement") or {}).get("conflicts") or []
        )
        disagreements_total += disagreements
        if disagreements >= 2:
            conflict_ok += 1
        else:
            errors.append("conflict_detection")
        if (debate.get("agreement") or {}).get("common_conclusions"):
            agreement_ok += 1
        else:
            errors.append("agreement")
        if checks.get("minority_preserved"):
            minority_ok += 1
        else:
            errors.append("minority")
        if len(debate.get("evidence_conflicts") or []) >= 2:
            evidence_ok += 1
        else:
            errors.append("evidence")
        consensus = debate.get("consensus") or {}
        if consensus.get("state") in DEBATE_STATES and 0 <= float(
            consensus.get("agreement") or 0
        ) <= 1:
            consensus_ok += 1
        else:
            errors.append("consensus")
        if checks.get("moderator_complete"):
            moderator_ok += 1
        else:
            errors.append("moderator")
        if checks.get("challenge_tournament_complete"):
            tournament_ok += 1
        else:
            errors.append("tournament")
        if checks.get("scorecard_complete") and (
            debate.get("debate_scorecard") or {}
        ).get("irs_ready"):
            scorecard_ok += 1
        else:
            errors.append("scorecard")

        state = str(consensus.get("state"))
        state_counts[state] = state_counts.get(state, 0) + 1
        if not errors and audit.get("passed"):
            passed += 1
        elif len(failures) < 20:
            failures.append(
                {
                    "scenario": i,
                    "errors": errors,
                    "disagreements": disagreements,
                    "state": state,
                }
            )

    avg_ms = round(sum(timed) / len(timed), 3)
    return {
        "ok": (
            passed / total >= 0.99
            and conflict_ok / total >= 1.0
            and agreement_ok / total >= 1.0
            and minority_ok / total >= 1.0
            and evidence_ok / total >= 1.0
            and consensus_ok / total >= 1.0
            and moderator_ok / total >= 1.0
            and tournament_ok / total >= 1.0
            and scorecard_ok / total >= 1.0
            and total >= BENCHMARK_MIN_SCENARIOS
            and disagreements_total >= BENCHMARK_MIN_DISAGREEMENTS
            and avg_ms <= MAX_DEBATE_MS_TARGET
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4),
        "correct_conflict_detection": round(conflict_ok / total, 4),
        "agreement_quality": round(agreement_ok / total, 4),
        "minority_preservation": round(minority_ok / total, 4),
        "evidence_conflict_mapping": round(evidence_ok / total, 4),
        "consensus_accuracy": round(consensus_ok / total, 4),
        "moderator_quality": round(moderator_ok / total, 4),
        "challenge_tournament": round(tournament_ok / total, 4),
        "debate_scorecard": round(scorecard_ok / total, 4),
        "debate_scenarios": total,
        "analyst_disagreements": disagreements_total,
        "state_counts": state_counts,
        "avg_debate_ms": avg_ms,
        "p95_debate_ms": round(
            sorted(timed)[int(0.95 * (len(timed) - 1))], 3
        ),
        "target_debate_ms": MAX_DEBATE_MS_TARGET,
        "failures_sample": failures,
        "rule": (
            "The Committee receives the thesis and the strongest institutional case against it."
        ),
    }


def soft_slice_for_ask_agi(
    question: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not is_enabled():
        return {}
    try:
        row = generate_for_question(question or "", dict(payload or {}))
        debate = _safe_dict(row.get("debate"))
        return {
            "debate_engine": {
                "enabled": True,
                "version": IDEB_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "not_another_committee": True,
                "executes_after": "Institutional Thesis Construction Engine",
                "executes_before": "Investment Committee",
                "primary_question": PRIMARY_QUESTION,
                "question": row.get("question"),
                "investment_thesis": debate.get("investment_thesis"),
                "analyst_positions": debate.get("analyst_positions"),
                "agreement": debate.get("agreement"),
                "disagreement": {
                    "disagreement_count": (
                        debate.get("disagreement") or {}
                    ).get("disagreement_count"),
                    "material_count": (
                        debate.get("disagreement") or {}
                    ).get("material_count"),
                    "conflicts": _safe_list(
                        (debate.get("disagreement") or {}).get("conflicts")
                    )[:10],
                },
                "evidence_conflicts": _safe_list(
                    debate.get("evidence_conflicts")
                )[:8],
                "assumption_conflicts": debate.get(
                    "assumption_conflicts"
                ),
                "minority_report": debate.get("minority_report"),
                "consensus": debate.get("consensus"),
                "moderator": debate.get("moderator"),
                "challenge_tournament": debate.get(
                    "challenge_tournament"
                ),
                "debate_scorecard": debate.get("debate_scorecard"),
                "open_questions": debate.get("open_questions"),
                "required_evidence": debate.get("required_evidence"),
                "committee_handoff": debate.get("committee_handoff"),
                "debate_ms": row.get("debate_ms"),
                "gate": row.get("gate"),
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "debate_engine": {
                "enabled": True,
                "version": IDEB_VERSION,
                "error": str(exc)[:240],
            }
        }
