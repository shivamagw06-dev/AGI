"""Institutional Hypothesis Generation Engine (IHG) V1 — RQ2 Sprint 1.

Soft-wired AFTER IREP (when available) and BEFORE first analyst research.
Not a top-level intelligence layer.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from hypothesis_engine.assumptions import enrich_assumptions
from hypothesis_engine.confidence import score_confidence
from hypothesis_engine.contradiction_detector import detect_contradictions
from hypothesis_engine.diagnostics import diagnose
from hypothesis_engine.evidence_map import build_evidence_map
from hypothesis_engine.flags import flags_dict, is_enabled
from hypothesis_engine.generator import generate_hypotheses
from hypothesis_engine.memory import memory_stats, remember_generation
from hypothesis_engine.quality_rules import evaluate_quality_rules
from hypothesis_engine.ranking import rank_hypotheses
from hypothesis_engine.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    HYPOTHESIS_TYPES,
    IHG_VERSION,
    MAX_GENERATION_MS_TARGET,
    PROGRAMME,
    PROGRAMME_SHORT,
    QUALITY_RULES,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)
from hypothesis_engine.taxonomy import taxonomy_stats


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000.0, 3)


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _entity_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    ere = _safe_dict(payload.get("entity_resolution"))
    # Ask AGI soft-slice nests under entity_resolution key
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
    cands = _safe_list(body.get("candidates"))
    if cands and isinstance(cands[0], dict):
        return cands[0]
    return {}


def _objective_from_payload(payload: dict[str, Any]) -> str | None:
    roe = _safe_dict(payload.get("research_objective"))
    nested = _safe_dict(roe.get("research_objective"))
    body = nested or roe
    obj = body.get("primary_objective") or body.get("objective")
    if isinstance(obj, list) and obj:
        return str(obj[0])
    if obj:
        return str(obj)
    return None


def _analysts_from_payload(payload: dict[str, Any]) -> list[str] | None:
    iar = _safe_dict(payload.get("analyst_router"))
    nested = _safe_dict(iar.get("analyst_router"))
    body = nested or iar
    ranked = _safe_list(body.get("ranked_analysts") or body.get("required_analysts") or body.get("selected_analysts"))
    names: list[str] = []
    for item in ranked:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("analyst") or item.get("role") or "").strip()
            if name:
                names.append(name)
        elif isinstance(item, str) and item.strip():
            names.append(item.strip())
    return names or None


def _hydrate_from_irep(payload: dict[str, Any]) -> dict[str, Any]:
    """Pull research_execution / RQ1 soft slices when present; never hard-depend."""
    out = dict(payload)
    re = _safe_dict(out.get("research_execution"))
    if not re:
        return out
    plan = _safe_dict(re.get("plan"))
    out.setdefault("entity_resolution", plan.get("entity_resolution") or re.get("entity_resolution"))
    out.setdefault("research_objective", plan.get("research_objective") or re.get("research_objective"))
    out.setdefault("analyst_router", plan.get("analyst_router") or re.get("analyst_router"))
    out.setdefault("question", plan.get("question") or re.get("question") or out.get("question"))
    return out


def _try_irep_build(question: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from research_execution.production import build_execution_package  # type: ignore

        return build_execution_package(question, payload)
    except Exception:
        return None


def generate_for_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Core generation path used by plan / diagnostics / soft-slice / quality gates."""
    started = time.perf_counter()
    payload = _hydrate_from_irep(dict(payload or {}))
    question = str(question or payload.get("question") or payload.get("q") or "").strip()

    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "ihg_version": IHG_VERSION,
            "generation_ms": _ms(started),
        }
    if not question:
        return {
            "ok": False,
            "error": "question is required",
            "ihg_version": IHG_VERSION,
            "generation_ms": _ms(started),
        }

    irep = None
    if not payload.get("research_execution"):
        irep = _try_irep_build(question, payload)
        if isinstance(irep, dict) and irep.get("ok"):
            payload = _hydrate_from_irep({**payload, "research_execution": irep})

    entity = _entity_from_payload(payload)
    objective = _objective_from_payload(payload) or payload.get("primary_objective")
    if objective is not None:
        objective = str(objective)
    analysts = _analysts_from_payload(payload)

    raw = generate_hypotheses(
        question=question,
        entity=entity or None,
        primary_objective=objective,
        required_analysts=analysts,
    )
    ranked_pack = rank_hypotheses(raw)
    ranked = list(ranked_pack.get("hypotheses") or [])
    ranked = enrich_assumptions(
        ranked,
        entity=entity or None,
        context=_safe_dict(payload.get("context_intelligence")),
    )
    evidence_map = build_evidence_map(ranked)
    contradictions = detect_contradictions(ranked)
    confidence = score_confidence(ranked)

    # Compact output contract per hypothesis
    compact = []
    for h in ranked:
        compact.append(
            {
                "id": h.get("id"),
                "hypothesis": h.get("statement"),
                "statement": h.get("statement"),
                "type": h.get("type"),
                "reason": h.get("reason"),
                "confidence": h.get("confidence"),
                "confidence_pct": round(float(h.get("confidence") or 0) * 100),
                "required_evidence": h.get("required_evidence"),
                "responsible_analysts": h.get("responsible_analysts"),
                "analyst_owner": (h.get("responsible_analysts") or ["Business"])[0],
                "priority": h.get("priority"),
                "status": h.get("status"),
                "assumptions": h.get("assumptions"),
                "falsification_test": h.get("falsification_test"),
                "quality_compliant": h.get("quality_compliant"),
                "quality_rules": h.get("quality_rules"),
                "impact_weight": h.get("impact_weight"),
                "rank_score": h.get("rank_score"),
            }
        )

    generation_ms = _ms(started)
    row = {
        "ok": True,
        "enabled": True,
        "engine": "hypothesis_engine",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IHG_VERSION,
        "ihg_version": IHG_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "IREP",
        "executes_before": "First analyst research",
        "primary_question": constitution_dict()["primary_question"],
        "question": question,
        "primary_objective": objective,
        "hypotheses": compact,
        "hypothesis_count": len(compact),
        "ranking": ranked_pack.get("ranking_by_type"),
        "ranking_by_type": ranked_pack.get("ranking_by_type"),
        "top_hypothesis_id": ranked_pack.get("top_hypothesis_id"),
        "evidence_map": evidence_map,
        "contradictions": contradictions,
        "overall_confidence": confidence.get("overall_confidence"),
        "confidence": confidence,
        "generation_ms": generation_ms,
        "metrics": {
            "generation_ms": generation_ms,
            "hypothesis_count": len(compact),
            "quality_compliant_count": sum(1 for h in compact if h.get("quality_compliant")),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "five_quality_rules": list(QUALITY_RULES),
        "generic_rejected": True,
        "irep_soft_imported": bool(irep and isinstance(irep, dict) and irep.get("ok")),
        "learning_hook": {"feed_into": "ILM", "stage": "pre_research_hypotheses"},
    }
    remember_generation(row)
    return row


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IHG_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_generation_ms_target": MAX_GENERATION_MS_TARGET,
        "taxonomy": taxonomy_stats(),
        "memory": memory_stats(),
        "not_a_top_level_intelligence_layer": True,
        "executes_after": "IREP",
        "executes_before": "First analyst research",
        "law": (
            "Institutional analysts begin by generating hypotheses that must be proven or disproven."
        ),
    }


def constitution() -> dict[str, Any]:
    return {
        "enabled": is_enabled(),
        **constitution_dict(),
        "flags": flags_dict(),
        "taxonomy": taxonomy_stats(),
    }


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "ihg_version": IHG_VERSION}
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
        row = generate_for_question(q, {"skip_iar": True})
        samples.append(
            {
                "question": q,
                "hypothesis_count": row.get("hypothesis_count"),
                "hypotheses": [
                    {
                        "id": h.get("id"),
                        "type": h.get("type"),
                        "hypothesis": h.get("hypothesis"),
                        "confidence": h.get("confidence_pct"),
                        "required_evidence": h.get("required_evidence"),
                        "analyst_owner": h.get("analyst_owner"),
                        "status": h.get("status"),
                        "priority": h.get("priority"),
                    }
                    for h in _safe_list(row.get("hypotheses"))
                ],
                "ranking": row.get("ranking"),
                "overall_confidence": row.get("overall_confidence"),
                "generation_ms": row.get("generation_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "ihg_version": IHG_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "primary_question": constitution_dict()["primary_question"],
        "five_quality_rules": list(QUALITY_RULES),
        "hypothesis_types": list(HYPOTHESIS_TYPES),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/hypothesis-engine"],
        "api_prefix": "/v1/hypothesis-engine",
        "display": {
            "question": "↓",
            "generated_hypotheses": "↓",
            "confidence": "↓",
            "required_evidence": "↓",
            "analyst_owner": "↓",
            "current_status": "↓",
        },
        "law": "Every institutional report begins with explicit hypotheses rather than implicit assumptions.",
        "not_a_top_level_intelligence_layer": True,
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


# --- Quality gates (≥1000 scenarios) ---

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "q": "Should I buy HDFC Bank?",
        "objective": "investment evaluation",
        "min_hypotheses": 4,
        "expect_types": ["Business", "Valuation", "Financial", "Competitive"],
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "objective": "historical analysis",
        "min_hypotheses": 3,
        "expect_types": ["Valuation", "Industry", "Macro"],
    },
    {
        "q": "Compare TCS vs Infosys",
        "objective": "peer comparison",
        "min_hypotheses": 2,
        "expect_types": ["Competitive", "Financial", "Valuation"],
    },
    {
        "q": "Explain ROIC",
        "objective": "educational",
        "min_hypotheses": 1,
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "objective": "macro impact",
        "min_hypotheses": 2,
        "expect_types": ["Macro"],
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "objective": "portfolio decision",
        "min_hypotheses": 1,
        "expect_types": ["Portfolio", "Risk"],
    },
    {
        "q": "What are the risks in Reliance Industries?",
        "objective": "risk assessment",
        "min_hypotheses": 2,
    },
    {
        "q": "Is Infosys overvalued on PE?",
        "objective": "valuation_assessment",
        "min_hypotheses": 2,
    },
]

_TEMPLATES: list[tuple[str, str]] = [
    ("Should I buy {name}?", "investment evaluation"),
    ("Should I sell {name}?", "investment evaluation"),
    ("Compare {name} vs {peer}", "peer comparison"),
    ("Explain {concept}", "educational"),
    ("Is {index} expensive versus history?", "historical analysis"),
    ("How will RBI rate cuts affect {sector}?", "macro impact"),
    ("Build a portfolio with {name}", "portfolio decision"),
    ("What are the risks in {name}?", "risk assessment"),
    ("Is {name} overvalued?", "valuation_assessment"),
    ("Assess business quality of {name}", "investment evaluation"),
    ("Forecast earnings for {name}", "forecast_assessment"),
    ("Does {name} deserve a growth premium?", "valuation_assessment"),
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
    "Kotak Mahindra Bank",
    "Asian Paints",
    "Bajaj Finance",
    "Nestle India",
    "L&T",
]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech", "ICICI Bank", "Axis Bank"]
_SECTORS = ["banks", "IT", "auto", "pharma", "FMCG"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "WACC", "CASA", "NIM"]


def _expanded() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    i = 0
    while len(cases) < 1100:
        tmpl, objective = _TEMPLATES[i % len(_TEMPLATES)]
        name = _NAMES[i % len(_NAMES)]
        peer = _PEERS[i % len(_PEERS)]
        if peer == name:
            peer = _PEERS[(i + 1) % len(_PEERS)]
        q = tmpl.format(
            name=name,
            peer=peer,
            sector=_SECTORS[i % len(_SECTORS)],
            index=_INDEXES[i % len(_INDEXES)],
            concept=_CONCEPTS[i % len(_CONCEPTS)],
        )
        cases.append({"q": q, "objective": objective, "min_hypotheses": 1, "kind": "template"})
        i += 1
    return cases


def _scenario_errors(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    hyps = _safe_list(row.get("hypotheses"))
    if len(hyps) < int(b.get("min_hypotheses") or 1):
        errs.append("coverage")
    # Mandatory fields
    for h in hyps:
        if not (
            h.get("id")
            and h.get("hypothesis")
            and h.get("reason")
            and h.get("confidence") is not None
            and h.get("required_evidence")
            and h.get("responsible_analysts")
            and h.get("priority") is not None
            and h.get("status")
        ):
            errs.append("fields")
            break
        if not h.get("quality_compliant"):
            errs.append("five_rules")
            break
        if len(str(h.get("hypothesis") or "")) < 48:
            errs.append("generic_length")
            break
        bad = evaluate_quality_rules(
            f"{b['q'][:24]} is a good company.",
            required_evidence=[],
        )
        if bad.get("passed"):
            errs.append("generic_allowed")
            break
    # Ranking consistency — priorities unique ascending from 1
    priorities = [int(h.get("priority") or 0) for h in hyps]
    if hyps and (priorities != list(range(1, len(hyps) + 1))):
        errs.append("ranking")
    # Expected types (soft — at least one overlap when specified)
    expect = set(b.get("expect_types") or [])
    if expect:
        got = {h.get("type") for h in hyps}
        if not (expect & got):
            errs.append("types")
    if float(row.get("generation_ms") or 0) > MAX_GENERATION_MS_TARGET * 5:
        errs.append("latency")
    return errs


def quality_gates() -> dict[str, Any]:
    cases = _expanded()
    passed = 0
    coverage_ok = rules_ok = generic_ok = ranking_ok = 0
    timed: list[float] = []
    failures: list[dict[str, Any]] = []

    for b in cases[:1100]:
        payload = {
            "primary_objective": b.get("objective"),
            "entity_resolution": {
                "canonical_name": "ScenarioCo",
                "ticker": "SCN",
            },
        }
        row = generate_for_question(b["q"], payload)
        timed.append(float(row.get("generation_ms") or 0))
        errs = _scenario_errors(b, row)

        if "coverage" not in errs and "fields" not in errs:
            coverage_ok += 1
        if "five_rules" not in errs:
            rules_ok += 1
        if "generic_length" not in errs and "generic_allowed" not in errs:
            generic_ok += 1
        if "ranking" not in errs:
            ranking_ok += 1

        if not errs:
            passed += 1
        elif len(failures) < 25:
            failures.append(
                {
                    "question": b["q"],
                    "errors": errs,
                    "hypothesis_count": row.get("hypothesis_count"),
                    "types": [h.get("type") for h in _safe_list(row.get("hypotheses"))],
                }
            )

    total = min(len(cases), 1100)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    return {
        "ok": (
            coverage_ok / total >= 1.0
            and rules_ok / total >= 1.0
            and generic_ok / total >= 1.0
            and ranking_ok / total >= 0.99
            and avg_ms <= MAX_GENERATION_MS_TARGET
            and total >= 1000
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "hypothesis_generation_coverage": round(coverage_ok / total, 4) if total else 0.0,
        "quality_rule_compliance": round(rules_ok / total, 4) if total else 0.0,
        "no_generic_hypotheses": round(generic_ok / total, 4) if total else 0.0,
        "ranking_consistency": round(ranking_ok / total, 4) if total else 0.0,
        "avg_generation_ms": avg_ms,
        "p95_generation_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_generation_ms": MAX_GENERATION_MS_TARGET,
        "failures_sample": failures,
        "rule": "Every Ask AGI request produces specific, testable, falsifiable hypotheses — never generics.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Ask AGI soft attachment — never raises into the request path."""
    if not is_enabled():
        return {}
    try:
        body = dict(payload or {})
        row = generate_for_question(question or "", body)
        hyps = _safe_list(row.get("hypotheses"))
        return {
            "hypothesis_engine": {
                "enabled": True,
                "version": IHG_VERSION,
                "sprint": SPRINT,
                "sprint_name": SPRINT_NAME,
                "not_a_top_level_intelligence_layer": True,
                "executes_after": "IREP",
                "executes_before": "First analyst research",
                "primary_question": constitution_dict()["primary_question"],
                "question": row.get("question"),
                "hypothesis_count": len(hyps),
                "hypotheses": [
                    {
                        "id": h.get("id"),
                        "hypothesis": h.get("hypothesis"),
                        "type": h.get("type"),
                        "confidence": h.get("confidence"),
                        "confidence_pct": h.get("confidence_pct"),
                        "required_evidence": h.get("required_evidence"),
                        "responsible_analysts": h.get("responsible_analysts"),
                        "analyst_owner": h.get("analyst_owner"),
                        "priority": h.get("priority"),
                        "status": h.get("status"),
                        "reason": h.get("reason"),
                    }
                    for h in hyps[:10]
                ],
                "ranking": row.get("ranking"),
                "overall_confidence": row.get("overall_confidence"),
                "contradictions": row.get("contradictions"),
                "evidence_map": {
                    "evidence_count": _safe_dict(row.get("evidence_map")).get("evidence_count"),
                    "unique_evidence_required": _safe_dict(row.get("evidence_map")).get(
                        "unique_evidence_required"
                    ),
                },
                "generation_ms": row.get("generation_ms"),
                "five_quality_rules": list(QUALITY_RULES),
                "generic_rejected": True,
            }
        }
    except Exception as exc:  # pragma: no cover
        return {
            "hypothesis_engine": {
                "enabled": True,
                "version": IHG_VERSION,
                "error": str(exc)[:240],
            }
        }
