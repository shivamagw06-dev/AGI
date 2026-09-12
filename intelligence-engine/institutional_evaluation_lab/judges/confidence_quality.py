"""Confidence Quality Score (CFQS) — independent IEL metric for Phase 4 Sprint 4.5.

Does NOT change CIO / overall pass weights / HQS / CQS.

Components:
  Calibration · Penalty correctness · Coverage influence · Committee influence ·
  Historical influence · Conflict influence · Explainability · Determinism

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

CFQS_VERSION = "cfqs-v1.0.0"

CFQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "calibration": 0.16,
    "penalty_correctness": 0.14,
    "coverage_influence": 0.12,
    "committee_influence": 0.12,
    "historical_influence": 0.10,
    "conflict_influence": 0.12,
    "explainability": 0.14,
    "determinism": 0.10,
}

_REPORT_FIELDS = (
    "overall_confidence",
    "confidence_level",
    "evidence_quality",
    "coverage_score",
    "hypothesis_strength",
    "hypothesis_separation",
    "conflict_score",
    "committee_agreement",
    "historical_score",
    "framework_consistency",
    "missing_evidence_penalty",
    "temporal_integrity",
    "replay_integrity",
    "confidence_reason",
    "confidence_version",
)


def _icc_pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("confidence_calibration") or {})


def _report(pack: dict[str, Any]) -> dict[str, Any]:
    return dict(pack.get("report") or {})


def _score_calibration(report: dict[str, Any]) -> tuple[float, str]:
    score = report.get("overall_confidence")
    if score is None:
        return 0.0, "missing_overall"
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.0, "non_numeric"
    if not (0 <= s <= 100):
        return 10.0, "out_of_range"
    level = str(report.get("confidence_level") or "")
    # Level must match numeric bands
    expected = (
        "Very High"
        if s >= 90
        else "High"
        if s >= 80
        else "Moderate"
        if s >= 60
        else "Low"
        if s >= 40
        else "Very Low"
    )
    if level != expected:
        return 55.0, f"level_mismatch:{level}!={expected}"
    if report.get("manually_assigned") is True or report.get("llm_used") is True:
        return 0.0, "manual_or_llm"
    return 100.0, "numeric_and_banded"


def _score_penalty_correctness(report: dict[str, Any]) -> tuple[float, str]:
    pen = report.get("missing_evidence_penalty")
    if pen is None:
        return 40.0, "missing_penalty_field"
    try:
        p = float(pen)
    except (TypeError, ValueError):
        return 20.0, "bad_penalty"
    missing = report.get("missing_evidence_that_would_raise") or []
    if missing and p <= 0:
        return 25.0, "missing_without_penalty"
    if not missing and p > 15:
        return 50.0, "penalty_without_listed_missing"
    if report.get("fixture_raised_confidence") is True:
        return 0.0, "fixture_raised"
    penalties = report.get("penalties") or {}
    if float(penalties.get("fixture_dependence") or 0) < 0:
        return 0.0, "negative_fixture_penalty"
    return 100.0, "penalties_coherent"


def _score_dim_present(report: dict[str, Any], key: str) -> tuple[float, str]:
    if report.get(key) is None:
        return 0.0, f"missing_{key}"
    try:
        v = float(report[key])
    except (TypeError, ValueError):
        return 20.0, f"bad_{key}"
    if 0 <= v <= 100:
        return 100.0, f"{key}={v:g}"
    return 40.0, f"out_of_range_{key}"


def _score_explainability(report: dict[str, Any]) -> tuple[float, str]:
    reason = str(report.get("confidence_reason") or "")
    if not reason:
        return 0.0, "no_reason"
    score = 40.0
    notes = []
    if "Confidence:" in reason and "/100" in reason:
        score += 25.0
        notes.append("numeric")
    if report.get("why_increased") is not None:
        score += 10.0
        notes.append("why_up")
    if report.get("why_decreased") is not None:
        score += 10.0
        notes.append("why_down")
    if report.get("missing_evidence_that_would_raise") is not None:
        score += 10.0
        notes.append("what_raises")
    if report.get("unresolved_conflicting_evidence") is not None or report.get(
        "evidence_reducing_confidence"
    ) is not None:
        score += 5.0
        notes.append("conflicts")
    return min(100.0, score), ",".join(notes) or "partial"


def _score_determinism(pack: dict[str, Any], report: dict[str, Any]) -> tuple[float, str]:
    if pack.get("llm_used") is True or report.get("llm_used") is True:
        return 0.0, "llm_used"
    if pack.get("manually_assigned") is True or report.get("manually_assigned") is True:
        return 0.0, "manual"
    if pack.get("deterministic") is False:
        return 40.0, "flag_false"
    # All required report fields present
    missing = [f for f in _REPORT_FIELDS if f not in report]
    if missing:
        return max(20.0, 100.0 - 10.0 * len(missing)), f"missing_fields={missing[:3]}"
    if report.get("temporal_integrity") is not True:
        return 60.0, "temporal_not_true"
    if report.get("replay_integrity") is not True:
        return 60.0, "replay_not_true"
    return 100.0, "deterministic_complete"


def judge_confidence_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    """Return CFQS judgment. Independent of DIMENSION_WEIGHTS / CIO / HQS / CQS."""
    _ = question
    pack = _icc_pack(probe)
    if not pack:
        return {
            "dimension": "confidence_quality",
            "score": None,
            "cfqs": None,
            "passed": True,
            "n_a": True,
            "cfqs_version": CFQS_VERSION,
            "independent_of_cio": True,
            "independent_of_hqs": True,
            "independent_of_cqs": True,
            "root_cause": None,
            "components": {},
            "note": "No confidence_calibration pack on probe",
        }

    report = _report(pack)
    components: dict[str, dict[str, Any]] = {}
    scorers = {
        "calibration": lambda: _score_calibration(report),
        "penalty_correctness": lambda: _score_penalty_correctness(report),
        "coverage_influence": lambda: _score_dim_present(report, "coverage_score"),
        "committee_influence": lambda: _score_dim_present(report, "committee_agreement"),
        "historical_influence": lambda: _score_dim_present(report, "historical_score"),
        "conflict_influence": lambda: _score_dim_present(report, "conflict_score"),
        "explainability": lambda: _score_explainability(report),
        "determinism": lambda: _score_determinism(pack, report),
    }
    for name, fn in scorers.items():
        s, reason = fn()
        components[name] = {"score": s, "reason": reason, "weight": CFQS_COMPONENT_WEIGHTS[name]}

    cfqs = 0.0
    for name, w in CFQS_COMPONENT_WEIGHTS.items():
        cfqs += w * float(components[name]["score"])
    cfqs = round(cfqs, 2)
    passed = cfqs >= 70.0
    worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
    root = None if passed else f"cfqs_weak_{worst[0]}"

    return {
        "dimension": "confidence_quality",
        "score": cfqs,
        "cfqs": cfqs,
        "passed": passed,
        "n_a": False,
        "component_weights": dict(CFQS_COMPONENT_WEIGHTS),
        "components": components,
        "overall_confidence": report.get("overall_confidence"),
        "confidence_level": report.get("confidence_level"),
        "cfqs_version": CFQS_VERSION,
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "independent_of_cqs": True,
        "root_cause": root,
    }


def aggregate_cfqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scores: list[float] = []
    component_sums: dict[str, list[float]] = {k: [] for k in CFQS_COMPONENT_WEIGHTS}
    n_a = 0
    for r in rows:
        j = ((r.get("dimensions") or {}).get("confidence_quality")) or r.get("confidence_quality") or {}
        if j.get("n_a") or (j.get("cfqs") is None and j.get("score") is None):
            n_a += 1
            continue
        s = j.get("cfqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_a += 1
            continue
        scores.append(float(s))
        comps = j.get("components") or {}
        for k in CFQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))
    n = len(scores)
    return {
        "cfqs_version": CFQS_VERSION,
        "n": n,
        "n_a": n_a,
        "mean_cfqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * sum(1 for s in scores if s >= 70.0) / n, 2) if n else None,
        "component_means": {
            k: (round(sum(v) / len(v), 2) if v else None) for k, v in component_sums.items()
        },
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "independent_of_cqs": True,
        "note": "CFQS does not affect IEL overall / CIO / HQS / CQS weights",
    }
