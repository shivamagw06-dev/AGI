"""Deterministic IST scoring — orchestration hard-gate + weighted rubric."""

from __future__ import annotations

from typing import Any, Mapping

from institutional_stress_tests.answer_contract import (
    detect_answer_failures,
    final_view_completeness,
    question_coverage,
)
from institutional_stress_tests.orchestration import evaluate_orchestration
from institutional_stress_tests.schema import PASS_SCORE, RUBRIC_WEIGHTS


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def score_rubric(answer: Mapping[str, Any], probes: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Score the nine rubric areas 0–1 each, then apply weights to 100."""
    sections = answer.get("sections") or {}
    view = answer.get("final_institutional_view") or {}
    hit = {m for m, r in probes.items() if r.get("contributing")}

    def has(*mods: str) -> float:
        return 1.0 if all(m in hit for m in mods) else (0.5 if any(m in hit for m in mods) else 0.0)

    qcov = question_coverage(sections)
    fview = final_view_completeness(view)
    supporting = view.get("evidence_supporting") or []
    against = view.get("evidence_against") or []
    unknowns = view.get("remaining_unknowns") or []
    refs = view.get("evidence_references") or answer.get("provenance") or []
    conf = view.get("confidence") if isinstance(view.get("confidence"), Mapping) else {}
    mean_c = conf.get("mean_confidence")
    calibration = bool(conf.get("calibration_notes")) or mean_c is not None

    def section_present(key: str) -> float:
        val = sections.get(key)
        if not isinstance(val, Mapping):
            return 0.0
        if val.get("status") == "missing":
            return 0.0
        return 1.0 if (val.get("text") or val.get("items") or val.get("points")) else 0.0

    scores = {
        "financial_reasoning": _clamp01(
            0.45 * has("FSE", "FIRE-01")
            + 0.25 * has("FIRE-02")
            + 0.30 * section_present("financial_quality_evolution")
        ),
        "business_reasoning": _clamp01(
            0.4 * has("FIRE-03") + 0.3 * has("FIRE-06") + 0.3 * section_present("temporary_or_structural")
        ),
        "evidence_consistency": _clamp01(
            0.5 * has("FIRE-04")
            + 0.3 * (1.0 if supporting and against else 0.4 if supporting or against else 0.0)
            + 0.2 * qcov["ratio"]
        ),
        "management_execution": _clamp01(
            0.7 * has("FIRE-05") + 0.3 * section_present("execution_vs_promises")
        ),
        "comparative_analysis": _clamp01(
            0.7 * has("CIO-01") + 0.3 * section_present("competitor_performance")
        ),
        "historical_timeline": _clamp01(
            0.4 * has("FIL") + 0.3 * has("WO-01") + 0.3 * has("FIRE-01", "FIRE-05")
        ),
        "missing_evidence_identification": _clamp01(
            0.5 * (1.0 if unknowns else 0.0)
            + 0.3 * section_present("missing_evidence")
            + 0.2 * fview["ratio"]
        ),
        "confidence_calibration": _clamp01(
            0.5 * (1.0 if calibration else 0.0)
            + 0.3 * (1.0 if unknowns else 0.0)
            + 0.2 * (1.0 if against else 0.0)
        ),
        "source_traceability": _clamp01(
            0.5 * (1.0 if refs else 0.0)
            + 0.3 * min(1.0, len(refs) / 5.0)
            + 0.2 * qcov["ratio"]
        ),
    }

    weighted_total = 0.0
    breakdown = []
    for area, weight in RUBRIC_WEIGHTS.items():
        s = float(scores.get(area) or 0.0)
        points = s * weight
        weighted_total += points
        breakdown.append({"area": area, "weight": weight, "score_0_1": round(s, 4), "points": round(points, 2)})

    return {
        "scores_0_1": {k: round(v, 4) for k, v in scores.items()},
        "breakdown": breakdown,
        "weighted_total": round(weighted_total, 2),
        "max_total": 100.0,
        "question_coverage": qcov,
        "final_view_completeness": fview,
    }


def score_case(
    case: Mapping[str, Any],
    probes: Mapping[str, Mapping[str, Any]],
    answer: Mapping[str, Any],
) -> dict[str, Any]:
    orch = evaluate_orchestration(
        probes,
        required=case.get("required_modules"),
        optional=case.get("optional_modules"),
    )
    answer_fails = detect_answer_failures(answer)
    rubric = score_rubric(answer, probes)

    auto_failures = list(orch.get("failures") or []) + [f["code"] for f in answer_fails]
    # Deduplicate preserving order
    seen: set[str] = set()
    auto_unique: list[str] = []
    for code in auto_failures:
        if code in seen:
            continue
        seen.add(code)
        auto_unique.append(code)

    weighted = float(rubric["weighted_total"])
    orchestration_ok = bool(orch.get("ok"))
    answer_ok = not answer_fails
    passed = orchestration_ok and answer_ok and weighted >= float(PASS_SCORE)

    # Hard rule: orchestration failure ⇒ overall FAIL regardless of rubric
    if not orchestration_ok:
        passed = False
    if answer_fails:
        passed = False

    return {
        "case_id": case.get("case_id"),
        "passed": passed,
        "pass_score": PASS_SCORE,
        "weighted_total": weighted,
        "orchestration": orch,
        "rubric": rubric,
        "automatic_failures": auto_unique,
        "answer_failure_details": answer_fails,
        "gates": {
            "orchestration": orchestration_ok,
            "answer_contract": answer_ok,
            "rubric_threshold": weighted >= float(PASS_SCORE),
            "no_single_module_pass": not orch.get("single_module"),
        },
        "summary": (
            "PASS — full-stack orchestration with institutional view"
            if passed
            else "FAIL — "
            + (
                "orchestration incomplete; "
                if not orchestration_ok
                else ""
            )
            + (
                f"automatic failures: {', '.join(auto_unique)}; "
                if auto_unique
                else ""
            )
            + (f"score {weighted}/{PASS_SCORE}" if weighted < PASS_SCORE or passed is False else "")
        ).strip(),
    }
