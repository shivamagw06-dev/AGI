"""Committee Quality Score (CQS) — independent IEL metric for Phase 4 Sprint 4.4.

Does NOT change CIO / overall pass weights.
Tracks committee deliberation quality separately from HQS and CIO.

Components:
  Bull completeness · Base realism · Bear completeness ·
  Probability calibration · Assumption quality · Catalyst quality ·
  Risk quality · Invalidation quality · Committee explainability

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

CQS_VERSION = "cqs-v1.0.0"

# Component weights within CQS (sum = 1.0)
CQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "bull_completeness": 0.12,
    "base_realism": 0.14,
    "bear_completeness": 0.12,
    "probability_calibration": 0.14,
    "assumption_quality": 0.10,
    "catalyst_quality": 0.08,
    "risk_quality": 0.10,
    "invalidation_quality": 0.10,
    "committee_explainability": 0.10,
}

_CASE_FIELDS = (
    "supporting_evidence",
    "contradictory_evidence",
    "underlying_assumptions",
    "required_conditions",
    "key_catalysts",
    "key_risks",
    "invalidation_conditions",
    "missing_evidence",
)


def _icr_pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("committee_reasoning") or {})


def _case_completeness(case: dict[str, Any] | None) -> tuple[float, str]:
    if not case:
        return 0.0, "absent"
    filled = 0
    for f in _CASE_FIELDS:
        v = case.get(f)
        if v is None:
            continue
        if isinstance(v, list) and len(v) == 0 and f == "contradictory_evidence":
            # Empty contradictory list is valid (retained, not fabricated)
            filled += 1
            continue
        if isinstance(v, list) and len(v) > 0:
            filled += 1
        elif not isinstance(v, list) and v:
            filled += 1
    # confidence + probability required
    if case.get("confidence") is not None:
        filled += 0.5
    if case.get("probability") is not None or case.get("probability_pct") is not None:
        filled += 0.5
    score = round(100.0 * filled / (len(_CASE_FIELDS) + 1), 1)
    return min(100.0, score), f"fields={filled}"


def _score_bull(pack: dict[str, Any]) -> tuple[float, str]:
    cases = pack.get("cases") or {}
    bull = cases.get("bull")
    if pack.get("report", {}).get("outcome") == "insufficient_evidence":
        return 85.0, "insufficient_no_fabrication"
    if not bull:
        # Not forcing three cases is correct — partial credit if explicit
        n = int(pack.get("n_cases") or 0)
        if n >= 1:
            return 70.0, "role_absent_not_forced"
        return 40.0, "no_cases"
    score, note = _case_completeness(bull)
    # Upside role should not be empty narrative
    if bull.get("supporting_evidence"):
        score = min(100.0, score + 5.0)
    return score, f"bull:{note}"


def _score_base(pack: dict[str, Any]) -> tuple[float, str]:
    cases = pack.get("cases") or {}
    base = cases.get("base")
    report = pack.get("report") or {}
    if report.get("outcome") == "insufficient_evidence":
        return 90.0, "insufficient_explicit"
    if not base:
        # Base should usually exist when cases exist
        if pack.get("n_cases"):
            return 45.0, "base_missing_with_cases"
        return 40.0, "no_cases"
    score, note = _case_completeness(base)
    # Realism: preferred/modal alignment + retained conflict
    if report.get("preferred_case") == "base":
        score = min(100.0, score + 5.0)
    if base.get("contradictory_evidence") is not None:
        score = min(100.0, score + 5.0)
    return min(100.0, score), f"base:{note}"


def _score_bear(pack: dict[str, Any]) -> tuple[float, str]:
    cases = pack.get("cases") or {}
    bear = cases.get("bear")
    if (pack.get("report") or {}).get("outcome") == "insufficient_evidence":
        return 85.0, "insufficient_no_fabrication"
    if not bear:
        n = int(pack.get("n_cases") or 0)
        if n >= 1:
            return 70.0, "role_absent_not_forced"
        return 40.0, "no_cases"
    score, note = _case_completeness(bear)
    if bear.get("key_risks"):
        score = min(100.0, score + 5.0)
    return score, f"bear:{note}"


def _score_probability(pack: dict[str, Any]) -> tuple[float, str]:
    report = pack.get("report") or {}
    if report.get("outcome") == "insufficient_evidence":
        dist = report.get("probability_distribution") or {}
        return (100.0, "empty_dist_ok") if not dist else (60.0, "unexpected_dist")
    dist = pack.get("probability_distribution") or report.get("probability_distribution") or {}
    if not dist:
        return 0.0, "missing_distribution"
    total = sum(float(v) for v in dist.values())
    if abs(total - 100.0) > 0.05:
        return 20.0, f"sum={total}"
    # Relative support — all present cases should have > 0
    if any(float(v) <= 0 for v in dist.values()):
        return 50.0, "zero_probability_case"
    if pack.get("voting_engine") is True:
        return 0.0, "voting_engine_flag"
    return 100.0, "calibrated_relative_support"


def _score_field_quality(pack: dict[str, Any], field: str) -> tuple[float, str]:
    cases = pack.get("cases") or {}
    present = [cases[r] for r in ("bull", "base", "bear") if cases.get(r)]
    if (pack.get("report") or {}).get("outcome") == "insufficient_evidence":
        return 90.0, "n_a_insufficient"
    if not present:
        return 0.0, "no_cases"
    ok = 0
    for c in present:
        v = c.get(field) or []
        if isinstance(v, list) and len(v) >= 1:
            ok += 1
        elif field == "contradictory_evidence" and isinstance(v, list):
            ok += 1  # retention of empty is fine
    score = round(100.0 * ok / len(present), 1)
    return score, f"{ok}/{len(present)}"


def _score_explainability(pack: dict[str, Any]) -> tuple[float, str]:
    report = pack.get("report") or {}
    if report.get("outcome") == "insufficient_evidence":
        summary = str(report.get("committee_summary") or "")
        return (95.0, "insufficient_explained") if "nsufficient" in summary else (60.0, "weak_insufficient")
    score = 40.0
    notes = []
    if report.get("why_preferred") or report.get("preferred_case"):
        score += 20.0
        notes.append("preferred")
    if report.get("why_alternatives_remain") or report.get("alternative_cases") is not None:
        score += 15.0
        notes.append("alts")
    if report.get("key_disagreements") is not None:
        score += 10.0
        notes.append("disagreements")
    if report.get("major_uncertainties") is not None:
        score += 10.0
        notes.append("uncertainties")
    if report.get("committee_summary"):
        score += 5.0
        notes.append("summary")
    if report.get("forced_consensus") is True or pack.get("voting_engine") is True:
        return 10.0, "forced_or_vote"
    return min(100.0, score), ",".join(notes) or "partial"


def judge_committee_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    """Return CQS judgment. Independent of DIMENSION_WEIGHTS / CIO / HQS."""
    _ = question  # signature parity with other judges
    pack = _icr_pack(probe)
    if not pack:
        return {
            "dimension": "committee_quality",
            "score": None,
            "cqs": None,
            "passed": True,
            "n_a": True,
            "cqs_version": CQS_VERSION,
            "independent_of_cio": True,
            "independent_of_hqs": True,
            "root_cause": None,
            "components": {},
            "note": "No committee_reasoning pack on probe",
        }

    components: dict[str, dict[str, Any]] = {}
    scorers = {
        "bull_completeness": lambda: _score_bull(pack),
        "base_realism": lambda: _score_base(pack),
        "bear_completeness": lambda: _score_bear(pack),
        "probability_calibration": lambda: _score_probability(pack),
        "assumption_quality": lambda: _score_field_quality(pack, "underlying_assumptions"),
        "catalyst_quality": lambda: _score_field_quality(pack, "key_catalysts"),
        "risk_quality": lambda: _score_field_quality(pack, "key_risks"),
        "invalidation_quality": lambda: _score_field_quality(pack, "invalidation_conditions"),
        "committee_explainability": lambda: _score_explainability(pack),
    }
    for name, fn in scorers.items():
        s, reason = fn()
        components[name] = {"score": s, "reason": reason, "weight": CQS_COMPONENT_WEIGHTS[name]}

    cqs = 0.0
    for name, w in CQS_COMPONENT_WEIGHTS.items():
        cqs += w * float(components[name]["score"])
    cqs = round(cqs, 2)
    passed = cqs >= 70.0
    worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
    root = None
    if not passed:
        root = f"cqs_weak_{worst[0]}"

    report = pack.get("report") or {}
    return {
        "dimension": "committee_quality",
        "score": cqs,
        "cqs": cqs,
        "passed": passed,
        "n_a": False,
        "component_weights": dict(CQS_COMPONENT_WEIGHTS),
        "components": components,
        "outcome": report.get("outcome"),
        "preferred_case": pack.get("preferred_case") or report.get("preferred_case"),
        "n_cases": pack.get("n_cases"),
        "voting_engine": False,
        "cqs_version": CQS_VERSION,
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "root_cause": root,
    }


def aggregate_cqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Suite-level CQS summary from scored rows."""
    scores: list[float] = []
    component_sums: dict[str, list[float]] = {k: [] for k in CQS_COMPONENT_WEIGHTS}
    n_a = 0
    for r in rows:
        j = ((r.get("dimensions") or {}).get("committee_quality")) or r.get("committee_quality") or {}
        if j.get("n_a") or (j.get("cqs") is None and j.get("score") is None):
            n_a += 1
            continue
        s = j.get("cqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_a += 1
            continue
        scores.append(float(s))
        comps = j.get("components") or {}
        for k in CQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))

    n = len(scores)
    return {
        "cqs_version": CQS_VERSION,
        "n": n,
        "n_a": n_a,
        "mean_cqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * sum(1 for s in scores if s >= 70.0) / n, 2) if n else None,
        "component_means": {
            k: (round(sum(v) / len(v), 2) if v else None) for k, v in component_sums.items()
        },
        "independent_of_cio": True,
        "independent_of_hqs": True,
        "note": "CQS does not affect IEL overall / CIO score weights",
    }
