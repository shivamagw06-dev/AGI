"""Institutional Hypothesis Testing Engine (IHTE) V1 — RQ2 Sprint 4.

Soft-wired AFTER Evidence Planning and BEFORE Business/Financial/Valuation analysts.
Not a top-level intelligence layer.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from hypothesis_testing.assumption_engine import build_assumptions
from hypothesis_testing.audit import coverage_audit
from hypothesis_testing.confidence_engine import score_result_confidence
from hypothesis_testing.contradiction_engine import score_contradictions
from hypothesis_testing.diagnostics import diagnose
from hypothesis_testing.effect_classifier import attach_effects, effect_breakdown
from hypothesis_testing.evidence_evaluator import gather_evidence_for_hypothesis
from hypothesis_testing.flags import flags_dict, is_enabled
from hypothesis_testing.hypothesis_registry import extract_hypotheses, register_hypotheses
from hypothesis_testing.probability_engine import status_from_probability, update_probability
from hypothesis_testing.reasoning_ledger import build_reasoning_ledger
from hypothesis_testing.schema import (
    ARCHITECTURE_STATUS,
    BENCHMARK_MIN_TESTED_HYPOTHESES,
    CONFIDENCE_THRESHOLD,
    EVIDENCE_EFFECTS,
    IHTE_VERSION,
    MAX_TESTING_MS_TARGET,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)
from hypothesis_testing.support_engine import score_support
from hypothesis_testing.uncertainty_engine import build_uncertainty


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _try_ihg(question: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from hypothesis_engine.production import generate_for_question as ihg_gen  # type: ignore

        row = ihg_gen(question, payload)
        wrap = {"hypothesis_engine": {"hypotheses": row.get("hypotheses") or []}}
        return extract_hypotheses(wrap)
    except Exception:
        return []


def _try_irq(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from research_questions.production import soft_slice_for_ask_agi as irq_soft  # type: ignore

        return irq_soft(question, payload) or {}
    except Exception:
        return {}


def _try_evidence_plan(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from acquisition_planner.production import soft_slice_for_ask_agi as iape_soft  # type: ignore

        return iape_soft(question, payload) or {}
    except Exception:
        try:
            from acquisition_planner.production import plan as iape_plan  # type: ignore

            return {"acquisition_planner": iape_plan({"question": question, **payload})}
        except Exception:
            return {}


def _fallback_hypotheses(question: str) -> list[dict[str, Any]]:
    q = question.lower()
    if "versus history" in q or ("expensive" in q and "history" in q):
        return extract_hypotheses(
            {
                "hypotheses": [
                    {
                        "id": "H1",
                        "type": "Valuation",
                        "statement": "The sector trades above its historical valuation range.",
                        "confidence": 0.78,
                    },
                    {
                        "id": "H2",
                        "type": "Industry",
                        "statement": "Current premium reflects AI optimism only partially supported by order books.",
                        "confidence": 0.64,
                    },
                ]
            }
        )
    return extract_hypotheses(
        {
            "hypotheses": [
                {
                    "id": "H1",
                    "type": "Business",
                    "statement": "HDFC possesses a durable funding advantage versus peers.",
                    "confidence": 0.82,
                },
                {
                    "id": "H2",
                    "type": "Valuation",
                    "statement": "Current valuation already reflects that franchise quality.",
                    "confidence": 0.63,
                },
                {
                    "id": "H3",
                    "type": "Financial",
                    "statement": "Credit costs remain structurally benign relative to peers.",
                    "confidence": 0.71,
                },
            ]
        }
    )


def test_hypothesis(hypothesis: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run full institutional test for one hypothesis."""
    payload = payload or {}
    raw_evidence = gather_evidence_for_hypothesis(hypothesis, payload)
    evidence = attach_effects(raw_evidence)

    support = score_support(evidence)
    contra = score_contradictions(evidence)
    assumptions = build_assumptions(hypothesis)
    uncertainty = build_uncertainty(evidence, assumptions=assumptions)
    missing_penalty = min(0.12, 0.04 * int(uncertainty.get("missing_count") or 0))

    prob = update_probability(
        float(hypothesis.get("initial_confidence") or 0.65),
        evidence,
        missing_penalty=missing_penalty,
    )
    status = status_from_probability(
        float(prob["updated_probability"]),
        support_count=int(support["support_count"]),
        contradiction_count=int(contra["contradiction_count"]),
        has_refutation=bool(contra.get("has_refutation")),
    )
    audit = coverage_audit(
        support_count=int(support["support_count"]),
        contradiction_count=int(contra["contradiction_count"]),
        evidence=evidence,
    )
    conf = score_result_confidence(
        support_count=int(support["support_count"]),
        contradiction_count=int(contra["contradiction_count"]),
        missing_count=int(uncertainty.get("missing_count") or 0),
        historical_count=int(audit["counts"]["historical"]),
        peer_count=int(audit["counts"]["peer"]),
        macro_count=int(audit["counts"]["macro"]),
        updated_probability=float(prob["updated_probability"]),
    )
    ledger = build_reasoning_ledger(
        hypothesis_id=str(hypothesis.get("id")),
        statement=str(hypothesis.get("statement") or hypothesis.get("hypothesis")),
        initial_confidence=float(hypothesis.get("initial_confidence") or 0.65),
        evidence=evidence,
        probability_timeline=list(prob.get("timeline") or []),
        status=status,
        updated_probability=float(prob["updated_probability"]),
    )
    neutral = [
        {"id": e.get("id"), "text": e.get("text"), "effect": e.get("effect")}
        for e in evidence
        if e.get("effect") == "Neutral" and e.get("polarity") != "missing"
    ]

    return {
        "id": hypothesis.get("id"),
        "hypothesis": hypothesis.get("statement") or hypothesis.get("hypothesis"),
        "type": hypothesis.get("type"),
        "initial_confidence": prob["initial_confidence"],
        "support_score": support["support_score"],
        "contradiction_score": contra["contradiction_score"],
        "supporting_evidence": support["supporting_evidence"],
        "contradicting_evidence": contra["contradicting_evidence"],
        "neutral_evidence": neutral,
        "missing_evidence": uncertainty.get("missing_evidence") or [],
        "updated_probability": prob["updated_probability"],
        "updated_probability_pct": round(float(prob["updated_probability"]) * 100),
        "net_delta": prob["net_delta"],
        "status": status,
        "assumptions": assumptions,
        "uncertainty": uncertainty,
        "confidence": conf["confidence"],
        "confidence_pct": conf["confidence_pct"],
        "confidence_interpretation": conf["interpretation"],
        "evidence_effects": [
            {
                "id": e.get("id"),
                "text": e.get("text"),
                "effect": e.get("effect"),
                "probability_delta": e.get("probability_delta"),
                "kind": e.get("kind"),
            }
            for e in evidence
            if e.get("polarity") != "missing"
        ],
        "effect_breakdown": effect_breakdown(evidence),
        "probability_timeline": prob.get("timeline"),
        "reasoning_ledger": ledger,
        "audit": audit,
        "decision": (
            "Proceed to analyst investigation"
            if status in ("Supported", "Partially Supported", "Inconclusive")
            else "Do not treat as base-case thesis"
        ),
    }


def generate_for_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(payload or {})
    question = str(question or payload.get("question") or payload.get("q") or "").strip()

    if not is_enabled():
        return {"ok": False, "enabled": False, "ihte_version": IHTE_VERSION, "testing_ms": _ms(started)}
    if not question:
        return {
            "ok": False,
            "error": "question is required",
            "ihte_version": IHTE_VERSION,
            "testing_ms": _ms(started),
        }

    hyps = extract_hypotheses(payload)
    ihg_imported = False
    if not hyps:
        hyps = _try_ihg(question, payload)
        ihg_imported = bool(hyps)
    if not hyps:
        hyps = _fallback_hypotheses(question)

    # Soft-enrich with IRQ / evidence plan when absent
    if not payload.get("research_questions"):
        irq = _try_irq(question, {**payload, "hypothesis_engine": {"hypotheses": hyps}})
        if irq:
            payload = {**payload, **irq}
    evidence_plan = _safe_dict(payload.get("acquisition_planner") or payload.get("evidence_plan"))
    if not evidence_plan:
        evidence_plan = _try_evidence_plan(question, payload)

    registry = register_hypotheses(hyps)
    tested = [test_hypothesis(h, payload) for h in hyps]
    testing_ms = _ms(started)

    matrix = [
        {
            "hypothesis": t.get("hypothesis"),
            "id": t.get("id"),
            "support": t.get("support_score"),
            "contradictions": t.get("contradiction_score"),
            "missing_evidence": t.get("missing_evidence"),
            "updated_probability": t.get("updated_probability"),
            "status": t.get("status"),
            "decision": t.get("decision"),
        }
        for t in tested
    ]

    row = {
        "ok": True,
        "enabled": True,
        "engine": "hypothesis_testing",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IHTE_VERSION,
        "ihte_version": IHTE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Evidence Planning",
        "executes_before": "Business / Financial / Valuation Analysts",
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        "registry": {"count": registry["count"], "by_type": registry["by_type"], "ids": registry["ids"]},
        "tested_hypotheses": tested,
        "tested_count": len(tested),
        "hypothesis_matrix": matrix,
        "evidence_plan_soft_imported": bool(evidence_plan),
        "ihg_soft_imported": ihg_imported,
        "testing_ms": testing_ms,
        "metrics": {
            "testing_ms": testing_ms,
            "tested_count": len(tested),
            "avg_updated_probability": round(
                sum(float(t.get("updated_probability") or 0) for t in tested) / max(len(tested), 1),
                4,
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "evidence_effects": list(EVIDENCE_EFFECTS),
        "enhancements": {"qualitative_evidence_effects": True, "reasoning_ledger": True},
        "gate": "No analyst may form an opinion until every assigned hypothesis has completed institutional testing.",
        "learning_hook": {"feed_into": "ILM", "stage": "pre_analyst_hypothesis_testing"},
    }
    return row


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IHTE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_testing_ms_target": MAX_TESTING_MS_TARGET,
        "evidence_effects": list(EVIDENCE_EFFECTS),
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Evidence Planning",
        "executes_before": "Business / Financial / Valuation Analysts",
        "enhancements": {"qualitative_evidence_effects": True, "reasoning_ledger": True},
        "law": PRIMARY_QUESTION,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "flags": flags_dict()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "ihte_version": IHTE_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    return generate_for_question(question, body)


def dashboard() -> dict[str, Any]:
    demos = [
        "Should I buy HDFC Bank?",
        "Is Nifty IT expensive versus history?",
        "Compare TCS vs Infosys",
    ]
    samples = []
    for q in demos:
        row = generate_for_question(q, {})
        samples.append(
            {
                "question": q,
                "tested_count": row.get("tested_count"),
                "matrix": row.get("hypothesis_matrix"),
                "hypotheses": [
                    {
                        "id": h.get("id"),
                        "hypothesis": h.get("hypothesis"),
                        "status": h.get("status"),
                        "initial_confidence": h.get("initial_confidence"),
                        "updated_probability": h.get("updated_probability"),
                        "support_score": h.get("support_score"),
                        "contradiction_score": h.get("contradiction_score"),
                        "missing_evidence": h.get("missing_evidence"),
                        "effect_breakdown": h.get("effect_breakdown"),
                        "reasoning_ledger": (h.get("reasoning_ledger") or [])[:6],
                        "supporting_evidence": (h.get("supporting_evidence") or [])[:4],
                        "contradicting_evidence": (h.get("contradicting_evidence") or [])[:3],
                    }
                    for h in _safe_list(row.get("tested_hypotheses"))
                ],
                "testing_ms": row.get("testing_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "ihte_version": IHTE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": PRIMARY_QUESTION,
        "evidence_effects": list(EVIDENCE_EFFECTS),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/hypothesis-testing"],
        "api_prefix": "/v1/hypothesis-testing",
        "display": {
            "question": "↓",
            "hypothesis": "↓",
            "supporting_evidence": "↓",
            "contradicting_evidence": "↓",
            "missing_evidence": "↓",
            "updated_confidence": "↓",
            "reasoning_timeline": "↓",
            "audit_trail": "↓",
        },
        "visual_flow": [
            "Hypothesis",
            "Evidence",
            "Support",
            "Contradictions",
            "Probability Update",
            "Result",
        ],
        "enhancements": {"qualitative_evidence_effects": True, "reasoning_ledger": True},
        "law": "Analysts receive tested hypotheses instead of raw evidence.",
        "not_a_top_level_intelligence_layer": True,
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


# --- IRS / quality gates ---

_TYPES = ["Business", "Financial", "Valuation", "Macro", "Risk", "Portfolio", "Industry", "Competitive", "Forecast"]
_NAMES = [
    "HDFC Bank",
    "Infosys",
    "TCS",
    "Reliance",
    "SBI",
    "ICICI Bank",
    "Wipro",
    "Titan",
    "ITC",
    "Axis Bank",
    "Kotak",
    "Asian Paints",
    "Bajaj Finance",
    "Nestle India",
    "L&T",
]


def _expanded_hypotheses() -> list[dict[str, Any]]:
    """Build ≥10,000 hypothesis test cases across required domains."""
    cases: list[dict[str, Any]] = []
    i = 0
    templates = [
        ("{name} possesses a durable franchise advantage versus peers.", "Business", 0.8),
        ("Current valuation of {name} already reflects franchise quality.", "Valuation", 0.63),
        ("Credit costs at {name} remain structurally benign versus peers.", "Financial", 0.71),
        ("Macro easing transmits to {name} primarily through NIM and volumes.", "Macro", 0.7),
        ("Regulatory or concentration risk could invalidate the thesis for {name}.", "Risk", 0.6),
        ("Adding {name} concentrates existing factor exposure in the portfolio.", "Portfolio", 0.58),
        ("Sector premium for {name} reflects growth optimism only partly evidenced.", "Industry", 0.64),
        ("Competition is narrowing historical advantages for {name}.", "Competitive", 0.66),
        ("Near-term growth for {name} may slow versus recent run-rates.", "Forecast", 0.58),
    ]
    while len(cases) < BENCHMARK_MIN_TESTED_HYPOTHESES + 50:
        tmpl, typ, conf = templates[i % len(templates)]
        name = _NAMES[i % len(_NAMES)]
        # Force type coverage
        typ = _TYPES[i % len(_TYPES)] if i % 3 == 0 else typ
        cases.append(
            {
                "id": f"BH-{i+1:05d}",
                "type": typ,
                "statement": tmpl.format(name=name),
                "hypothesis": tmpl.format(name=name),
                "initial_confidence": conf,
                "question": f"Should I buy {name}?",
            }
        )
        i += 1
    return cases


def quality_gates() -> dict[str, Any]:
    cases = _expanded_hypotheses()[:BENCHMARK_MIN_TESTED_HYPOTHESES]
    passed = 0
    attr_ok = support_ok = contra_ok = prob_ok = unc_ok = 0
    timed: list[float] = []
    failures: list[dict[str, Any]] = []
    type_counts: dict[str, int] = {}

    # Batch by question for realism, but score per hypothesis
    # Faster path: test_hypothesis directly
    for h in cases:
        t0 = time.perf_counter()
        row = test_hypothesis(
            {
                "id": h["id"],
                "type": h["type"],
                "statement": h["statement"],
                "hypothesis": h["hypothesis"],
                "initial_confidence": h["initial_confidence"],
            },
            {},
        )
        elapsed = _ms(t0)
        timed.append(elapsed)
        type_counts[h["type"]] = type_counts.get(h["type"], 0) + 1

        errs: list[str] = []
        # Attribution
        if not row.get("supporting_evidence") and not row.get("contradicting_evidence"):
            errs.append("attribution")
        else:
            attr_ok += 1
        # Support scoring
        if row.get("support_score") is None:
            errs.append("support")
        else:
            support_ok += 1
        # Contradiction scoring
        if row.get("contradiction_score") is None:
            errs.append("contradiction")
        else:
            contra_ok += 1
        # Probability update
        if row.get("updated_probability") is None or row.get("initial_confidence") is None:
            errs.append("probability")
        elif not row.get("probability_timeline"):
            errs.append("probability")
        else:
            prob_ok += 1
        # Uncertainty
        unc = row.get("uncertainty") or {}
        if not unc or "known" not in unc or "missing_evidence" not in unc:
            errs.append("uncertainty")
        else:
            unc_ok += 1
        # Effects + ledger
        if not row.get("evidence_effects") or not row.get("reasoning_ledger"):
            errs.append("enhancements")
        # Audit minima
        if not (row.get("audit") or {}).get("passed"):
            errs.append("audit")

        if not errs:
            passed += 1
        elif len(failures) < 25:
            failures.append({"id": h["id"], "type": h["type"], "errors": errs, "status": row.get("status")})

    total = len(cases)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    required_types = {"Business", "Financial", "Valuation", "Macro", "Risk", "Portfolio"}
    return {
        "ok": (
            attr_ok / total >= 1.0
            and support_ok / total >= 1.0
            and contra_ok / total >= 1.0
            and prob_ok / total >= 1.0
            and unc_ok / total >= 1.0
            and passed / total >= 0.99
            and total >= BENCHMARK_MIN_TESTED_HYPOTHESES
            and required_types.issubset(set(type_counts))
            and avg_ms <= MAX_TESTING_MS_TARGET
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "evidence_attribution": round(attr_ok / total, 4) if total else 0.0,
        "support_scoring": round(support_ok / total, 4) if total else 0.0,
        "contradiction_scoring": round(contra_ok / total, 4) if total else 0.0,
        "probability_updates": round(prob_ok / total, 4) if total else 0.0,
        "uncertainty_reporting": round(unc_ok / total, 4) if total else 0.0,
        "tested_hypotheses": total,
        "type_counts": type_counts,
        "avg_testing_ms": avg_ms,
        "p95_testing_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_testing_ms": MAX_TESTING_MS_TARGET,
        "failures_sample": failures,
        "rule": "No analyst may form an opinion until every assigned hypothesis has completed institutional testing.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    try:
        row = generate_for_question(question or "", dict(payload or {}))
        tested = []
        for h in _safe_list(row.get("tested_hypotheses"))[:8]:
            tested.append(
                {
                    "id": h.get("id"),
                    "hypothesis": h.get("hypothesis"),
                    "type": h.get("type"),
                    "initial_confidence": h.get("initial_confidence"),
                    "support_score": h.get("support_score"),
                    "contradiction_score": h.get("contradiction_score"),
                    "missing_evidence": h.get("missing_evidence"),
                    "updated_probability": h.get("updated_probability"),
                    "updated_probability_pct": h.get("updated_probability_pct"),
                    "status": h.get("status"),
                    "assumptions": h.get("assumptions"),
                    "uncertainty": {
                        "missing_count": (h.get("uncertainty") or {}).get("missing_count"),
                        "conflict_intensity": (h.get("uncertainty") or {}).get("conflict_intensity"),
                        "known_unknowns": (h.get("uncertainty") or {}).get("known_unknowns"),
                    },
                    "confidence": h.get("confidence"),
                    "effect_breakdown": h.get("effect_breakdown"),
                    "evidence_effects": (h.get("evidence_effects") or [])[:8],
                    "reasoning_ledger": (h.get("reasoning_ledger") or [])[:10],
                    "decision": h.get("decision"),
                }
            )
        return {
            "hypothesis_testing": {
                "enabled": True,
                "version": IHTE_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "executes_after": "Evidence Planning",
                "executes_before": "Business / Financial / Valuation Analysts",
                "primary_question": PRIMARY_QUESTION,
                "question": row.get("question"),
                "tested_count": row.get("tested_count"),
                "tested_hypotheses": tested,
                "hypothesis_matrix": row.get("hypothesis_matrix"),
                "testing_ms": row.get("testing_ms"),
                "evidence_effects": list(EVIDENCE_EFFECTS),
                "enhancements": {"qualitative_evidence_effects": True, "reasoning_ledger": True},
                "gate": row.get("gate"),
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "hypothesis_testing": {
                "enabled": True,
                "version": IHTE_VERSION,
                "error": str(exc)[:240],
            }
        }
