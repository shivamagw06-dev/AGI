"""Institutional Thesis Construction Engine (ITCE) V1 — RQ2 Sprint 7.

Soft-wired AFTER the Bayesian Belief & Confidence Engine and BEFORE the
Investment Committee. Not a top-level intelligence layer.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from thesis_engine.catalyst_engine import build_catalysts, catalyst_summary
from thesis_engine.contradiction_resolver import resolve_contradictions
from thesis_engine.conviction_engine import compute_conviction, thesis_state
from thesis_engine.conviction_waterfall import build_conviction_waterfall
from thesis_engine.dependency_graph import build_dependency_graph
from thesis_engine.diagnostics import diagnose
from thesis_engine.evolution_engine import build_evolution
from thesis_engine.flags import flags_dict, is_enabled
from thesis_engine.interaction_matrix import build_interaction_matrix
from thesis_engine.monitoring_engine import build_monitoring_dashboard
from thesis_engine.narrative_engine import build_narratives
from thesis_engine.pillar_engine import build_pillars, pillar_summary
from thesis_engine.pressure_gauge import build_pressure_gauge
from thesis_engine.quality_score import score_thesis_quality
from thesis_engine.schema import (
    ARCHITECTURE_STATUS,
    BENCHMARK_MIN_THESES,
    CONFIDENCE_THRESHOLD,
    ITCE_VERSION,
    MAX_BUILD_MS_TARGET,
    PILLARS,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    THESIS_STATES,
    constitution_dict,
)
from thesis_engine.thesis_builder import build_core_thesis, build_thesis_breaking_conditions
from thesis_engine.thesis_dna import build_thesis_dna
from thesis_engine.thesis_quality import audit_thesis
from thesis_engine.thesis_registry import extract_beliefs, register_thesis
from thesis_engine.timeline_engine import build_timeline
from thesis_engine.stability_engine import assess_stability


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _try_bbce(question: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        from belief_engine.production import generate_for_question as bbce_gen  # type: ignore

        row = bbce_gen(question, payload)
        return extract_beliefs({"belief_engine": {"beliefs": row.get("beliefs")}})
    except Exception:
        return []


def _fallback_beliefs(question: str) -> list[dict[str, Any]]:
    q = question.lower()
    if "versus history" in q or ("expensive" in q and "history" in q):
        seeds = [
            ("H1", "Valuation", "The sector trades above its historical valuation range.", 0.74, 0.68),
            ("H2", "Industry", "Premium reflects growth optimism only partly evidenced.", 0.6, 0.6),
            ("H3", "Forecast", "Limited multiple expansion without upper-quartile growth.", 0.63, 0.6),
        ]
    else:
        seeds = [
            ("H1", "Business", "The franchise retains a durable funding advantage versus peers.", 0.76, 0.66),
            ("H2", "Valuation", "Current valuation already reflects franchise quality.", 0.6, 0.62),
            ("H3", "Financial", "Credit costs remain structurally benign versus peers.", 0.7, 0.64),
            ("H4", "Competitive", "Competition is narrowing historical advantages.", 0.55, 0.6),
            ("H5", "Macro", "Policy easing transmits through funding costs and volumes.", 0.6, 0.58),
            ("H6", "Portfolio", "Position concentrates existing financials factor exposure.", 0.52, 0.57),
        ]
    out = []
    for hid, typ, stmt, posterior, conf in seeds:
        out.append(
            {
                "hypothesis_id": hid,
                "hypothesis": stmt,
                "type": typ,
                "prior_belief": round(posterior - 0.05, 4),
                "posterior_belief": posterior,
                "belief_state": "Supported" if posterior >= 0.68 else "Leaning Positive" if posterior >= 0.58 else "Neutral",
                "confidence": conf,
                "uncertainty": {"known_unknowns": [f"Unverified driver for {hid}"], "missing_evidence": [f"Pending data for {hid}"]},
                "drift": {"drift_level": "stable"},
                "supporting_evidence": [
                    {"text": f"Supporting observation {i} for {hid}", "support_score": 80 + i}
                    for i in range(1, 4)
                ],
                "contradicting_evidence": [
                    {"text": f"Challenging observation {i} for {hid}", "contradiction_score": 65 + i}
                    for i in range(1, 3)
                ],
                "missing_evidence": [f"Pending data for {hid}"],
            }
        )
    return out


def build_thesis(
    beliefs: list[dict[str, Any]],
    *,
    question: str = "",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct one institutional investment thesis from the belief package."""
    payload = payload or {}
    pillars = build_pillars(beliefs)
    dependency = build_dependency_graph(pillars)  # mutates pillar confidence via propagation
    interaction_matrix = build_interaction_matrix(pillars)
    contradictions = resolve_contradictions(beliefs, pillars)

    core_seed_conviction = compute_conviction(pillars, contradictions=contradictions)
    entity_hint = build_core_thesis(
        question=question,
        payload=payload,
        pillars=pillars,
        conviction=core_seed_conviction,
        contradictions=contradictions,
    )
    catalysts = build_catalysts(pillars, entity=entity_hint.get("entity") or "the subject")
    cat_summary = catalyst_summary(catalysts)
    conviction = compute_conviction(pillars, contradictions=contradictions, catalysts_summary=cat_summary)
    core = build_core_thesis(
        question=question,
        payload=payload,
        pillars=pillars,
        conviction=conviction,
        contradictions=contradictions,
    )
    timeline = build_timeline(catalysts)
    breakers = build_thesis_breaking_conditions(pillars, contradictions)

    summary = pillar_summary(pillars)
    status = thesis_state(
        float(conviction["overall"]),
        supported_pillars=int(summary["supported"]),
        major_contradictions=int(contradictions.get("major_count") or 0),
    )
    # Thesis confidence: mean pillar confidence, discounted by missing evidence
    missing = _safe_list(contradictions.get("missing_evidence"))
    base_conf = sum(float(p["confidence"]) for p in pillars) / max(len(pillars), 1)
    confidence = round(max(0.2, min(0.95, base_conf - min(0.15, 0.02 * len(missing)))), 4)
    quality = score_thesis_quality(
        pillars,
        contradictions,
        calibration=confidence,
    )
    prior_snapshots = _safe_list(
        payload.get("thesis_history")
        or _safe_dict(payload.get("institutional_memory")).get("thesis_history")
    )
    stability = assess_stability(
        float(conviction["overall"]),
        prior_snapshots=prior_snapshots,
        pillar_strengths=[float(p["strength"]) for p in pillars],
    )
    dna = build_thesis_dna(
        core.get("entity") or "The subject",
        pillars,
        thesis_breaking_conditions=breakers,
    )
    pressure = build_pressure_gauge(pillars, contradictions)
    monitoring = build_monitoring_dashboard(pillars, breakers)
    waterfall = build_conviction_waterfall(
        pillars,
        conviction,
        pressure_penalties={
            "Contradictions": min(0.08, 0.012 * int(contradictions.get("major_count") or 0)),
            "Missing Evidence": min(0.05, 0.008 * len(missing)),
        },
    )
    narratives = build_narratives(
        core,
        pillars,
        contradictions,
        catalysts,
        conviction,
        status,
    )
    evolution = build_evolution(
        current_conviction=float(conviction["overall"]),
        status=status,
        core_thesis=str(core.get("statement") or ""),
        prior_snapshots=prior_snapshots,
    )

    risks = [
        {
            "risk": c["event"],
            "pillar": c["pillar"],
            "probability": c["probability"],
            "timing": c["expected_timing"],
        }
        for c in catalysts
        if c["polarity"] == "Negative"
    ][:5]

    thesis = {
        "core_thesis": core,
        "supporting_pillars": pillars,
        "pillar_summary": summary,
        "dependency_graph": dependency,
        "pillar_interaction_matrix": interaction_matrix,
        "contradictions": contradictions,
        "disconfirming_evidence": contradictions.get("strongest_contradicting_evidence"),
        "catalysts": catalysts,
        "catalyst_summary": cat_summary,
        "risks": risks,
        "thesis_breaking_conditions": breakers,
        "timeline": timeline,
        "confidence": confidence,
        "confidence_pct": round(confidence * 100),
        "conviction": conviction,
        "quality": quality,
        "stability": stability,
        "narratives": narratives,
        "thesis_dna": dna,
        "conviction_waterfall": waterfall,
        "monitoring": monitoring,
        "evolution": evolution,
        "pressure_gauge": pressure,
        "missing_evidence": missing,
        "status": status,
        "committee_handoff": {
            "debate_this": core.get("statement"),
            "strongest_support": (contradictions.get("strongest_supporting_evidence") or [{}])[0].get("text"),
            "strongest_challenge": (contradictions.get("strongest_contradicting_evidence") or [{}])[0].get("text"),
            "outstanding_questions": contradictions.get("outstanding_questions"),
        },
    }
    thesis["audit"] = audit_thesis(thesis)
    return thesis


def generate_for_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(payload or {})
    question = str(question or payload.get("question") or payload.get("q") or "").strip()

    if not is_enabled():
        return {"ok": False, "enabled": False, "itce_version": ITCE_VERSION, "build_ms": _ms(started)}
    if not question:
        return {"ok": False, "error": "question is required", "itce_version": ITCE_VERSION, "build_ms": _ms(started)}

    beliefs = extract_beliefs(payload)
    bbce_imported = False
    if not beliefs:
        beliefs = _try_bbce(question, payload)
        bbce_imported = bool(beliefs)
    if not beliefs:
        beliefs = _fallback_beliefs(question)

    thesis = build_thesis(beliefs, question=question, payload=payload)
    build_ms = _ms(started)

    return {
        "ok": True,
        "enabled": True,
        "engine": "thesis_engine",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ITCE_VERSION,
        "itce_version": ITCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Bayesian Belief & Confidence Engine",
        "executes_before": "Investment Committee",
        "primary_question": PRIMARY_QUESTION,
        "question": question,
        "belief_count": len(beliefs),
        "thesis": thesis,
        "institutional_investment_thesis": thesis,
        "registry": register_thesis(thesis),
        "bbce_soft_imported": bbce_imported,
        "build_ms": build_ms,
        "metrics": {
            "build_ms": build_ms,
            "belief_count": len(beliefs),
            "pillar_count": len(thesis.get("supporting_pillars") or []),
            "catalyst_count": len(thesis.get("catalysts") or []),
            "conviction": (thesis.get("conviction") or {}).get("overall"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "gate": "The Committee debates one coherent thesis — not disconnected analyst reports.",
        "learning_hook": {"feed_into": "ILM", "stage": "institutional_thesis_construction"},
    }


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ITCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_build_ms_target": MAX_BUILD_MS_TARGET,
        "pillars": list(PILLARS),
        "thesis_states": list(THESIS_STATES),
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "Bayesian Belief & Confidence Engine",
        "executes_before": "Investment Committee",
        "law": PRIMARY_QUESTION,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "flags": flags_dict()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "itce_version": ITCE_VERSION}
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
        t = row.get("thesis") or {}
        samples.append(
            {
                "question": q,
                "core_thesis": (t.get("core_thesis") or {}).get("statement"),
                "status": t.get("status"),
                "conviction": (t.get("conviction") or {}).get("overall"),
                "confidence": t.get("confidence"),
                "quality": t.get("quality"),
                "stability": t.get("stability"),
                "pressure_gauge": t.get("pressure_gauge"),
                "pillars": [
                    {
                        "pillar": p.get("pillar"),
                        "strength": p.get("strength"),
                        "confidence": p.get("confidence"),
                        "verdict": p.get("verdict"),
                    }
                    for p in _safe_list(t.get("supporting_pillars"))
                ],
                "catalyst_summary": t.get("catalyst_summary"),
                "timeline": (t.get("timeline") or {}).get("horizons"),
                "narratives": t.get("narratives"),
                "thesis_dna": t.get("thesis_dna"),
                "build_ms": row.get("build_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "itce_version": ITCE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": PRIMARY_QUESTION,
        "pillars": list(PILLARS),
        "thesis_states": list(THESIS_STATES),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/thesis-construction"],
        "api_prefix": "/v1/thesis-engine",
        "display": {
            "core_thesis": "↓",
            "supporting_pillars": "↓",
            "evidence": "↓",
            "contradictions": "↓",
            "catalysts": "↓",
            "timeline": "↓",
            "conviction": "↓",
            "status": "↓",
            "quality": "↓",
            "stability": "↓",
            "pressure": "↓",
        },
        "visual_flow": [
            "Core Thesis",
            "Business",
            "Financial",
            "Valuation",
            "Macro",
            "Portfolio",
            "Investment Committee",
        ],
        "law": "Analysts submit one coherent institutional investment thesis.",
        "not_a_top_level_intelligence_layer": True,
        "world_class_extensions": [
            "pillar_interaction_matrix",
            "thesis_stability",
            "quality_score",
            "multi_length_narratives",
            "thesis_dna",
            "conviction_waterfall",
            "threshold_monitoring",
            "versioned_evolution",
            "thesis_pressure_gauge",
        ],
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


# --- IRS / quality gates ---

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
]
_TYPES = ["Business", "Financial", "Valuation", "Competitive", "Macro", "Portfolio", "Capital Allocation", "Industry"]


def _synthetic_beliefs(seed: int) -> list[dict[str, Any]]:
    beliefs = []
    for j, typ in enumerate(_TYPES):
        # Vary posterior across the spectrum to exercise all thesis states
        posterior = round(min(0.92, max(0.12, 0.3 + ((seed * 7 + j * 11) % 60) / 100.0)), 4)
        beliefs.append(
            {
                "hypothesis_id": f"S{seed}-H{j+1}",
                "hypothesis": f"Synthetic {typ} hypothesis {seed}-{j}",
                "type": typ,
                "prior_belief": round(max(0.1, posterior - 0.06), 4),
                "posterior_belief": posterior,
                "belief_state": "Supported" if posterior >= 0.68 else "Neutral" if posterior >= 0.45 else "Challenged",
                "confidence": round(0.45 + ((seed + j) % 40) / 100.0, 4),
                "uncertainty": {"known_unknowns": [f"unknown-{j}"], "missing_evidence": [f"gap-{j}"] if j % 3 == 0 else []},
                "supporting_evidence": [
                    {"text": f"support {k} for {typ} {seed}", "support_score": 70 + k} for k in range(1, 4)
                ],
                "contradicting_evidence": [
                    {"text": f"challenge {k} for {typ} {seed}", "contradiction_score": 60 + k} for k in range(1, 3)
                ],
                "missing_evidence": [f"gap-{j}"] if j % 3 == 0 else [],
            }
        )
    return beliefs


def quality_gates() -> dict[str, Any]:
    total = BENCHMARK_MIN_THESES
    passed = 0
    construction_ok = consistency_ok = pillar_ok = contra_ok = catalyst_ok = conviction_ok = 0
    interaction_ok = stability_ok = quality_ok = monitoring_ok = 0
    timed: list[float] = []
    state_counts: dict[str, int] = {}
    failures: list[dict[str, Any]] = []

    for i in range(total):
        name = _NAMES[i % len(_NAMES)]
        question = f"Should I buy {name}?"
        beliefs = _synthetic_beliefs(i)
        t0 = time.perf_counter()
        thesis = build_thesis(beliefs, question=question, payload={})
        timed.append(_ms(t0))

        errs: list[str] = []
        audit = thesis.get("audit") or {}
        checks = audit.get("checks") or {}

        if checks.get("core_thesis_present"):
            construction_ok += 1
        else:
            errs.append("construction")
        if checks.get("logical_consistency"):
            consistency_ok += 1
        else:
            errs.append("consistency")
        if checks.get("min_supporting_pillars"):
            pillar_ok += 1
        else:
            errs.append("pillars")
        if checks.get("min_major_contradictions"):
            contra_ok += 1
        else:
            errs.append("contradictions")
        if checks.get("min_catalysts"):
            catalyst_ok += 1
        else:
            errs.append("catalysts")

        conviction = float((thesis.get("conviction") or {}).get("overall") or 0)
        if 0.0 < conviction < 1.0 and thesis.get("status") in THESIS_STATES:
            conviction_ok += 1
        else:
            errs.append("conviction")

        if not checks.get("min_thesis_breaking_conditions"):
            errs.append("breakers")

        matrix = thesis.get("pillar_interaction_matrix") or {}
        if len(matrix.get("values") or []) == len(PILLARS) and matrix.get("edges"):
            interaction_ok += 1
        else:
            errs.append("interaction")
        quality = thesis.get("quality") or {}
        if quality.get("separate_from_conviction") and quality.get("overall") is not None:
            quality_ok += 1
        else:
            errs.append("quality")
        stability = thesis.get("stability") or {}
        if stability.get("trend") in ("Stable", "Improving", "Weakening", "Volatile"):
            stability_ok += 1
        else:
            errs.append("stability")
        pressure = thesis.get("pressure_gauge") or {}
        monitoring = thesis.get("monitoring") or {}
        if (
            pressure.get("level") in ("Low", "Moderate", "High", "Critical")
            and monitoring.get("conditions")
            and thesis.get("conviction_waterfall")
            and thesis.get("thesis_dna")
            and thesis.get("evolution")
        ):
            monitoring_ok += 1
        else:
            errs.append("monitoring")

        state_counts[str(thesis.get("status"))] = state_counts.get(str(thesis.get("status")), 0) + 1

        if not errs:
            passed += 1
        elif len(failures) < 20:
            failures.append({"index": i, "errors": errs, "status": thesis.get("status")})

    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    return {
        "ok": (
            construction_ok / total >= 1.0
            and consistency_ok / total >= 1.0
            and pillar_ok / total >= 1.0
            and contra_ok / total >= 1.0
            and catalyst_ok / total >= 1.0
            and conviction_ok / total >= 1.0
            and interaction_ok / total >= 1.0
            and stability_ok / total >= 1.0
            and quality_ok / total >= 1.0
            and monitoring_ok / total >= 1.0
            and passed / total >= 0.99
            and total >= BENCHMARK_MIN_THESES
            and avg_ms <= MAX_BUILD_MS_TARGET
            and len(state_counts) >= 2
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "thesis_construction": round(construction_ok / total, 4),
        "logical_consistency": round(consistency_ok / total, 4),
        "pillar_completeness": round(pillar_ok / total, 4),
        "contradiction_handling": round(contra_ok / total, 4),
        "catalyst_quality": round(catalyst_ok / total, 4),
        "conviction_calibration": round(conviction_ok / total, 4),
        "interaction_quantification": round(interaction_ok / total, 4),
        "stability_tracking": round(stability_ok / total, 4),
        "quality_separation": round(quality_ok / total, 4),
        "pressure_monitoring": round(monitoring_ok / total, 4),
        "theses_built": total,
        "state_counts": state_counts,
        "avg_build_ms": avg_ms,
        "p95_build_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_build_ms": MAX_BUILD_MS_TARGET,
        "failures_sample": failures,
        "rule": "Every thesis carries pillars, contradictions, catalysts and a thesis-breaking condition.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    try:
        row = generate_for_question(question or "", dict(payload or {}))
        t = _safe_dict(row.get("thesis"))
        return {
            "thesis_engine": {
                "enabled": True,
                "version": ITCE_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "executes_after": "Bayesian Belief & Confidence Engine",
                "executes_before": "Investment Committee",
                "primary_question": PRIMARY_QUESTION,
                "question": row.get("question"),
                "core_thesis": t.get("core_thesis"),
                "supporting_pillars": [
                    {
                        "pillar": p.get("pillar"),
                        "strength": p.get("strength"),
                        "strength_pct": p.get("strength_pct"),
                        "confidence": p.get("confidence"),
                        "verdict": p.get("verdict"),
                        "belief_ids": p.get("belief_ids"),
                        "contradictions": (p.get("contradictions") or [])[:2],
                    }
                    for p in _safe_list(t.get("supporting_pillars"))
                ],
                "contradictions": {
                    "major": _safe_list((t.get("contradictions") or {}).get("major"))[:4],
                    "outstanding_questions": (t.get("contradictions") or {}).get("outstanding_questions"),
                },
                "catalysts": _safe_list(t.get("catalysts"))[:8],
                "catalyst_summary": t.get("catalyst_summary"),
                "risks": t.get("risks"),
                "thesis_breaking_conditions": t.get("thesis_breaking_conditions"),
                "timeline": t.get("timeline"),
                "confidence": t.get("confidence"),
                "conviction": t.get("conviction"),
                "quality": t.get("quality"),
                "stability": t.get("stability"),
                "pressure_gauge": t.get("pressure_gauge"),
                "conviction_waterfall": t.get("conviction_waterfall"),
                "pillar_interaction_matrix": t.get("pillar_interaction_matrix"),
                "monitoring": t.get("monitoring"),
                "evolution": t.get("evolution"),
                "thesis_dna": t.get("thesis_dna"),
                "narratives": t.get("narratives"),
                "missing_evidence": t.get("missing_evidence"),
                "status": t.get("status"),
                "committee_handoff": t.get("committee_handoff"),
                "build_ms": row.get("build_ms"),
                "gate": row.get("gate"),
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "thesis_engine": {
                "enabled": True,
                "version": ITCE_VERSION,
                "error": str(exc)[:240],
            }
        }
