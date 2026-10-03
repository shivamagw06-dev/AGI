"""Institutional Research Question Engine (IRQ) V1 — RQ2 Sprint 2.

Soft-wired AFTER Hypothesis Generation (IHG) and BEFORE Evidence Collection.
Not a top-level intelligence layer.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from research_questions.analyst_assignment import assign_owners
from research_questions.dependency_graph import attach_trees
from research_questions.diagnostics import diagnose
from research_questions.evidence_mapping import evidence_rollup, map_evidence
from research_questions.flags import flags_dict, is_enabled
from research_questions.generator import generate_question_sets
from research_questions.memory import memory_stats, remember_generation
from research_questions.priority_engine import prioritise, priority_breakdown
from research_questions.quality_rules import coverage_report, evaluate_question_quality
from research_questions.question_library import library_stats
from research_questions.schema import (
    ARCHITECTURE_STATUS,
    BENCHMARK_HYPOTHESIS_SETS,
    BENCHMARK_MIN_QUESTIONS,
    CONFIDENCE_THRESHOLD,
    IRQ_VERSION,
    MAX_GENERATION_MS_TARGET,
    MIN_QUESTIONS_PER_HYPOTHESIS,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    QUALITY_RULES,
    QUESTION_TYPES,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)
from research_questions.scoring import attach_scores, impact_summary


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _entity_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    ere = _safe_dict(payload.get("entity_resolution"))
    nested = _safe_dict(ere.get("entity_resolution"))
    body = nested or ere
    primary = _safe_dict(body.get("primary_entity") or body.get("entity"))
    if primary:
        return primary
    if body.get("ticker") or body.get("canonical_name") or body.get("name"):
        return {
            "ticker": body.get("ticker"),
            "canonical_name": body.get("canonical_name") or body.get("name"),
            "peers": body.get("peers") or [],
        }
    return {}


def _hypotheses_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    # Prefer nested Ask AGI soft-slice
    ihg = _safe_dict(payload.get("hypothesis_engine"))
    nested = _safe_dict(ihg.get("hypothesis_engine"))
    body = nested or ihg
    hyps = _safe_list(body.get("hypotheses") or payload.get("hypotheses"))
    out = []
    for h in hyps:
        if not isinstance(h, dict):
            continue
        out.append(
            {
                "id": h.get("id"),
                "statement": h.get("statement") or h.get("hypothesis"),
                "hypothesis": h.get("hypothesis") or h.get("statement"),
                "type": h.get("type") or "Business",
                "confidence": h.get("confidence"),
            }
        )
    return out


def _try_ihg(question: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from hypothesis_engine.production import generate_for_question  # type: ignore

        row = generate_for_question(question, payload)
        return [
            {
                "id": h.get("id"),
                "statement": h.get("statement") or h.get("hypothesis"),
                "hypothesis": h.get("hypothesis") or h.get("statement"),
                "type": h.get("type") or "Business",
                "confidence": h.get("confidence"),
            }
            for h in _safe_list(row.get("hypotheses"))
            if isinstance(h, dict)
        ]
    except Exception:
        return []


def _fallback_hypotheses(question: str) -> list[dict[str, Any]]:
    """Minimal hypotheses when IHG is unavailable — still enables IRQ."""
    q = question.lower()
    if "versus history" in q or ("expensive" in q and "history" in q):
        return [
            {
                "id": "H1",
                "type": "Valuation",
                "statement": "The sector trades above its historical valuation range on forward multiples.",
                "hypothesis": "The sector trades above its historical valuation range on forward multiples.",
                "confidence": 0.78,
            },
            {
                "id": "H2",
                "type": "Industry",
                "statement": "Current premium reflects AI optimism only partially supported by order books.",
                "hypothesis": "Current premium reflects AI optimism only partially supported by order books.",
                "confidence": 0.64,
            },
        ]
    return [
        {
            "id": "H1",
            "type": "Business",
            "statement": "The subject possesses a durable funding or franchise advantage versus peers.",
            "hypothesis": "The subject possesses a durable funding or franchise advantage versus peers.",
            "confidence": 0.75,
        },
        {
            "id": "H2",
            "type": "Valuation",
            "statement": "Current valuation already reflects that quality advantage.",
            "hypothesis": "Current valuation already reflects that quality advantage.",
            "confidence": 0.63,
        },
        {
            "id": "H3",
            "type": "Financial",
            "statement": "Credit costs remain structurally benign relative to peers.",
            "hypothesis": "Credit costs remain structurally benign relative to peers.",
            "confidence": 0.7,
        },
    ]


def generate_for_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(payload or {})
    question = str(question or payload.get("question") or payload.get("q") or "").strip()

    if not is_enabled():
        return {"ok": False, "enabled": False, "irq_version": IRQ_VERSION, "generation_ms": _ms(started)}
    if not question:
        return {
            "ok": False,
            "error": "question is required",
            "irq_version": IRQ_VERSION,
            "generation_ms": _ms(started),
        }

    hyps = _hypotheses_from_payload(payload)
    ihg_imported = False
    if not hyps:
        hyps = _try_ihg(question, payload)
        ihg_imported = bool(hyps)
    if not hyps:
        hyps = _fallback_hypotheses(question)

    entity = _entity_from_payload(payload)
    blocks = generate_question_sets(ask_question=question, hypotheses=hyps, entity=entity or None)

    # Pipeline: evidence → scores → owners → priority → tree
    processed_blocks = []
    all_questions: list[dict[str, Any]] = []
    for block in blocks:
        qs = list(block.get("research_questions") or [])
        qs = map_evidence(qs)
        qs = attach_scores(qs)
        qs = assign_owners(qs)
        qs = prioritise(qs)
        # Re-number after priority sort for stable display
        for i, q in enumerate(qs, start=1):
            q["id"] = f"{block.get('hypothesis_id')}-Q{i}"
        cov = coverage_report(qs)
        processed_blocks.append(
            {
                **block,
                "research_questions": qs,
                "question_count": len(qs),
                "coverage": cov,
                "priority_breakdown": priority_breakdown(qs),
                "impact_summary": impact_summary(qs),
            }
        )
        all_questions.extend(qs)

    processed_blocks = attach_trees(processed_blocks)
    # Flatten compact output contract (after tree enrichment for dependencies)
    compact_questions = []
    all_questions = []
    for block in processed_blocks:
        for q in _safe_list(block.get("research_questions")):
            all_questions.append(q)
            compact_questions.append(
                {
                    "id": q.get("id"),
                    "research_question": q.get("question"),
                    "question": q.get("question"),
                    "type": q.get("type"),
                    "priority": q.get("priority"),
                    "analyst_owner": q.get("analyst_owner"),
                    "required_evidence": q.get("required_evidence"),
                    "dependencies": q.get("dependencies") or [],
                    "status": q.get("status") or "Waiting",
                    "confidence": q.get("confidence"),
                    "decision_impact": q.get("decision_impact"),
                    "decision_impact_label": q.get("decision_impact_label"),
                    "hypothesis_id": q.get("hypothesis_id"),
                    "tree_layer": q.get("tree_layer"),
                    "quality_compliant": q.get("quality_compliant"),
                }
            )

    answered = sum(1 for q in compact_questions if q.get("status") == "Answered")
    contradicted = sum(1 for q in compact_questions if q.get("status") == "Contradicted")
    waiting = sum(1 for q in compact_questions if q.get("status") == "Waiting")
    total_q = len(compact_questions)
    coverage_pct = round(answered / total_q, 4) if total_q else 0.0
    sets_ok = sum(1 for b in processed_blocks if (b.get("coverage") or {}).get("meets_minima"))

    generation_ms = _ms(started)
    row = {
        "ok": True,
        "enabled": True,
        "engine": "research_questions",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IRQ_VERSION,
        "irq_version": IRQ_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "IHG / Hypothesis Generation",
        "executes_before": "Evidence Collection",
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        "hypotheses": hyps,
        "hypothesis_count": len(hyps),
        "hypothesis_question_sets": processed_blocks,
        "research_questions": compact_questions,
        "research_question_count": total_q,
        "priority_breakdown": priority_breakdown(all_questions),
        "impact_summary": impact_summary(all_questions),
        "evidence_rollup": evidence_rollup(all_questions),
        "coverage": {
            "questions_generated": total_q,
            "questions_answered": answered,
            "questions_unanswered": waiting,
            "questions_contradicted": contradicted,
            "coverage_pct": coverage_pct,
            "hypothesis_sets_meeting_minima": sets_ok,
            "hypothesis_sets_total": len(processed_blocks),
            "min_questions_per_hypothesis": MIN_QUESTIONS_PER_HYPOTHESIS,
        },
        "generation_ms": generation_ms,
        "metrics": {
            "generation_ms": generation_ms,
            "research_question_count": total_q,
            "hypothesis_count": len(hyps),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "five_quality_rules": list(QUALITY_RULES),
        "ihg_soft_imported": ihg_imported,
        "learning_hook": {"feed_into": "ILM", "stage": "pre_evidence_research_questions"},
        "gate": "No hypothesis may proceed to evidence collection until research questions are generated.",
    }
    remember_generation(row)
    return row


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IRQ_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_generation_ms_target": MAX_GENERATION_MS_TARGET,
        "library": library_stats(),
        "memory": memory_stats(),
        "question_types": list(QUESTION_TYPES),
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "IHG / Hypothesis Generation",
        "executes_before": "Evidence Collection",
        "enhancements": {"question_tree": True, "decision_impact_score": True},
        "law": PRIMARY_QUESTION,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "flags": flags_dict(), "library": library_stats()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "irq_version": IRQ_VERSION}
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
                "hypothesis_count": row.get("hypothesis_count"),
                "research_question_count": row.get("research_question_count"),
                "coverage": row.get("coverage"),
                "sets": [
                    {
                        "hypothesis_id": b.get("hypothesis_id"),
                        "hypothesis": b.get("hypothesis"),
                        "question_count": b.get("question_count"),
                        "proof_chain": (b.get("question_tree") or {}).get("proof_chain"),
                        "top_questions": [
                            {
                                "id": qq.get("id"),
                                "question": qq.get("question"),
                                "priority": qq.get("priority"),
                                "analyst_owner": qq.get("analyst_owner"),
                                "required_evidence": qq.get("required_evidence"),
                                "status": qq.get("status"),
                                "confidence": qq.get("confidence"),
                                "decision_impact": qq.get("decision_impact"),
                            }
                            for qq in (b.get("research_questions") or [])[:6]
                        ],
                    }
                    for b in _safe_list(row.get("hypothesis_question_sets"))
                ],
                "generation_ms": row.get("generation_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "irq_version": IRQ_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": PRIMARY_QUESTION,
        "five_quality_rules": list(QUALITY_RULES),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/research-questions"],
        "api_prefix": "/v1/research-questions",
        "display": {
            "question": "↓",
            "hypothesis": "↓",
            "research_questions": "↓",
            "priority": "↓",
            "analyst_owner": "↓",
            "evidence_needed": "↓",
            "status": "↓",
            "confidence": "↓",
        },
        "enhancements": {"question_tree": True, "decision_impact_score": True},
        "law": "Analysts answer research questions. Hypotheses become measurable investigations.",
        "not_a_top_level_intelligence_layer": True,
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


# --- Quality / IRS gates ---

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {"q": "Should I buy HDFC Bank?", "min_hypotheses": 2},
    {"q": "Is Nifty IT expensive versus history?", "min_hypotheses": 2},
    {"q": "Compare TCS vs Infosys", "min_hypotheses": 1},
    {"q": "How will RBI rate cuts affect banks?", "min_hypotheses": 1},
    {"q": "Build a ₹500,000 portfolio", "min_hypotheses": 1},
    {"q": "What are the risks in Reliance Industries?", "min_hypotheses": 1},
    {"q": "Is Infosys overvalued on PE?", "min_hypotheses": 1},
    {"q": "Explain ROIC", "min_hypotheses": 1},
]

_TEMPLATES = [
    "Should I buy {name}?",
    "Is {index} expensive versus history?",
    "Compare {name} vs {peer}",
    "What are the risks in {name}?",
    "How will RBI rate cuts affect {sector}?",
    "Does {name} deserve a growth premium?",
    "Build a portfolio with {name}",
    "Is {name} overvalued?",
]

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
_PEERS = ["Infosys", "TCS", "Wipro", "ICICI Bank", "Axis Bank"]
_SECTORS = ["banks", "IT", "auto", "pharma", "FMCG"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50"]


def _expanded_sets() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    i = 0
    while len(cases) < BENCHMARK_HYPOTHESIS_SETS + 20:
        tmpl = _TEMPLATES[i % len(_TEMPLATES)]
        name = _NAMES[i % len(_NAMES)]
        peer = _PEERS[i % len(_PEERS)]
        if peer == name:
            peer = _PEERS[(i + 1) % len(_PEERS)]
        q = tmpl.format(
            name=name,
            peer=peer,
            sector=_SECTORS[i % len(_SECTORS)],
            index=_INDEXES[i % len(_INDEXES)],
        )
        cases.append({"q": q, "min_hypotheses": 1, "kind": "template"})
        i += 1
    return cases


def _set_errors(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    blocks = _safe_list(row.get("hypothesis_question_sets"))
    if len(blocks) < int(b.get("min_hypotheses") or 1):
        errs.append("hypotheses")
    total_q = int(row.get("research_question_count") or 0)
    if total_q < MIN_QUESTIONS_PER_HYPOTHESIS:
        errs.append("coverage_total")

    for block in blocks:
        cov = block.get("coverage") or coverage_report(list(block.get("research_questions") or []))
        if not cov.get("meets_minima"):
            errs.append("minima")
            break
        # Ownership: exactly one owner
        for q in block.get("research_questions") or []:
            if not q.get("analyst_owner"):
                errs.append("ownership")
                break
            if not q.get("required_evidence"):
                errs.append("evidence")
                break
            if not q.get("quality_compliant"):
                errs.append("quality")
                break
            if q.get("decision_impact") is None:
                errs.append("impact")
                break
        if "ownership" in errs or "evidence" in errs or "quality" in errs:
            break
        tree = block.get("question_tree") or {}
        if not tree.get("proof_chain") or not tree.get("edges"):
            errs.append("tree")
            break

    # Generic rejection probe
    bad = evaluate_question_quality("Tell me about the company", required_evidence=[])
    if bad.get("passed"):
        errs.append("generic_allowed")

    if float(row.get("generation_ms") or 0) > MAX_GENERATION_MS_TARGET * 8:
        errs.append("latency")
    return errs


def quality_gates() -> dict[str, Any]:
    cases = _expanded_sets()[:BENCHMARK_HYPOTHESIS_SETS]
    passed = 0
    relevance_ok = quality_ok = unique_ok = evidence_ok = ownership_ok = coverage_ok = 0
    timed: list[float] = []
    total_questions = 0
    failures: list[dict[str, Any]] = []

    for b in cases:
        row = generate_for_question(
            b["q"],
            {"entity_resolution": {"canonical_name": "ScenarioCo", "ticker": "SCN"}},
        )
        timed.append(float(row.get("generation_ms") or 0))
        total_questions += int(row.get("research_question_count") or 0)
        errs = _set_errors(b, row)

        if "hypotheses" not in errs and "minima" not in errs and "coverage_total" not in errs:
            coverage_ok += 1
            relevance_ok += 1
        if "quality" not in errs and "generic_allowed" not in errs:
            quality_ok += 1
        if "minima" not in errs:  # uniqueness embedded in minima
            unique_ok += 1
        if "evidence" not in errs:
            evidence_ok += 1
        if "ownership" not in errs:
            ownership_ok += 1

        if not errs:
            passed += 1
        elif len(failures) < 25:
            failures.append(
                {
                    "question": b["q"],
                    "errors": errs,
                    "research_question_count": row.get("research_question_count"),
                    "hypothesis_count": row.get("hypothesis_count"),
                }
            )

    total = len(cases)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    return {
        "ok": (
            coverage_ok / total >= 1.0
            and quality_ok / total >= 1.0
            and unique_ok / total >= 1.0
            and evidence_ok / total >= 1.0
            and ownership_ok / total >= 1.0
            and relevance_ok / total >= 1.0
            and total >= BENCHMARK_HYPOTHESIS_SETS
            and total_questions >= BENCHMARK_MIN_QUESTIONS
            and avg_ms <= MAX_GENERATION_MS_TARGET
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "question_relevance": round(relevance_ok / total, 4) if total else 0.0,
        "question_quality": round(quality_ok / total, 4) if total else 0.0,
        "question_uniqueness": round(unique_ok / total, 4) if total else 0.0,
        "evidence_mapping": round(evidence_ok / total, 4) if total else 0.0,
        "analyst_ownership": round(ownership_ok / total, 4) if total else 0.0,
        "coverage": round(coverage_ok / total, 4) if total else 0.0,
        "hypothesis_sets": total,
        "research_questions_generated": total_questions,
        "avg_generation_ms": avg_ms,
        "p95_generation_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_generation_ms": MAX_GENERATION_MS_TARGET,
        "benchmark": {
            "min_hypothesis_sets": BENCHMARK_HYPOTHESIS_SETS,
            "min_research_questions": BENCHMARK_MIN_QUESTIONS,
        },
        "failures_sample": failures,
        "rule": "No hypothesis proceeds to evidence collection without research questions.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    try:
        body = dict(payload or {})
        row = generate_for_question(question or "", body)
        sets = []
        for b in _safe_list(row.get("hypothesis_question_sets"))[:6]:
            sets.append(
                {
                    "hypothesis_id": b.get("hypothesis_id"),
                    "hypothesis": b.get("hypothesis"),
                    "question_count": b.get("question_count"),
                    "proof_chain": (b.get("question_tree") or {}).get("proof_chain"),
                    "priority_breakdown": b.get("priority_breakdown"),
                    "research_questions": [
                        {
                            "id": q.get("id"),
                            "question": q.get("question"),
                            "priority": q.get("priority"),
                            "analyst_owner": q.get("analyst_owner"),
                            "required_evidence": q.get("required_evidence"),
                            "dependencies": q.get("dependencies"),
                            "status": q.get("status"),
                            "confidence": q.get("confidence"),
                            "decision_impact": q.get("decision_impact"),
                            "type": q.get("type"),
                        }
                        for q in _safe_list(b.get("research_questions"))[:12]
                    ],
                }
            )
        return {
            "research_questions": {
                "enabled": True,
                "version": IRQ_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "executes_after": "IHG / Hypothesis Generation",
                "executes_before": "Evidence Collection",
                "primary_question": PRIMARY_QUESTION,
                "question": row.get("question"),
                "hypothesis_count": row.get("hypothesis_count"),
                "research_question_count": row.get("research_question_count"),
                "hypothesis_question_sets": sets,
                "coverage": row.get("coverage"),
                "impact_summary": row.get("impact_summary"),
                "priority_breakdown": row.get("priority_breakdown"),
                "generation_ms": row.get("generation_ms"),
                "five_quality_rules": list(QUALITY_RULES),
                "enhancements": {"question_tree": True, "decision_impact_score": True},
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "research_questions": {
                "enabled": True,
                "version": IRQ_VERSION,
                "error": str(exc)[:240],
            }
        }
