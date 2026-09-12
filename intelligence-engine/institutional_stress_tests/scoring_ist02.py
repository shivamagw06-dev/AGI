"""IST-02 scoring — pass ≥ 85; quality failures hard-gate."""

from __future__ import annotations

from typing import Any, Mapping

from institutional_stress_tests.schema_ist02 import IST02_PASS_SCORE, IST02_REPORT_SECTIONS, IST02_RUBRIC_WEIGHTS


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def score_ist02(
    report: Mapping[str, Any],
    quality: Mapping[str, Any],
    modules: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    sections = report.get("sections") or {}
    codes = set(quality.get("failure_codes") or [])

    struct_ratio = sum(1 for k in IST02_REPORT_SECTIONS if k in sections) / max(1, len(IST02_REPORT_SECTIONS))
    fin_ok = 1.0 if sections.get("financial_analysis") else 0.0
    biz_ok = 1.0 if sections.get("business_quality") and sections.get("business_context") else 0.0
    evid_cov = float(quality.get("citation_coverage") or 0.0)
    contra_n = len((sections.get("evidence_contradicting") or {}).get("items") or [])
    support_n = len((sections.get("evidence_supporting") or {}).get("items") or [])
    conf = sections.get("confidence_discussion") or {}
    conf_ok = 1.0 if (
        conf.get("confidence") is not None
        and conf.get("drivers_increasing_confidence")
        and conf.get("drivers_reducing_confidence")
        and conf.get("reason_confidence_cannot_be_higher")
    ) else 0.0
    peer_ok = 1.0 if (sections.get("peer_comparison") or {}).get("paragraphs") else 0.0
    mon = sections.get("monitoring_framework") or {}
    mon_ok = 1.0 if mon.get("next_quarter") and mon.get("six_month") and mon.get("twelve_month") else 0.0
    cf_ok = 1.0 if (sections.get("counterfactual_analysis") or {}).get("items") else 0.0
    writing = 1.0
    if report.get("collapsed_to_buy_sell"):
        writing = 0.2
    if "HALLUCINATED_FACT" in codes:
        writing = min(writing, 0.3)

    # Module contribution bonus (reuse, not new intelligence)
    mod_hit = sum(
        1
        for m in ("FIRE-01", "FIRE-02", "FIRE-03", "FIRE-04", "FIRE-05", "FIRE-06", "CIO-01")
        if (modules.get(m) or {}).get("ok")
    )
    mod_ratio = mod_hit / 7.0

    scores = {
        "research_structure": _clamp01(struct_ratio),
        "financial_reasoning": _clamp01(0.6 * fin_ok + 0.4 * mod_ratio),
        "business_reasoning": _clamp01(0.6 * biz_ok + 0.4 * mod_ratio),
        "evidence_quality": _clamp01(0.5 * evid_cov + 0.3 * (1.0 if support_n else 0.0) + 0.2 * cf_ok),
        "counter_evidence": _clamp01(min(1.0, contra_n / 2.0)),
        "confidence_calibration": _clamp01(conf_ok),
        "peer_comparison": _clamp01(peer_ok),
        "monitoring_framework": _clamp01(mon_ok),
        "source_traceability": _clamp01(0.7 * evid_cov + 0.3 * (0.0 if "PROVENANCE_MISSING" in codes else 1.0)),
        "institutional_writing_quality": _clamp01(
            0.5 * writing + 0.3 * (1.0 if sections.get("alternative_interpretations") else 0.0) + 0.2 * cf_ok
        ),
    }

    weight_sum = sum(float(w) for w in IST02_RUBRIC_WEIGHTS.values()) or 100.0
    raw_points = 0.0
    breakdown = []
    for area, weight in IST02_RUBRIC_WEIGHTS.items():
        s = float(scores.get(area) or 0.0)
        pts = s * float(weight)
        raw_points += pts
        # Normalize area points onto a 100-point scale (spec weights may sum ≠ 100)
        norm_pts = pts * (100.0 / weight_sum)
        breakdown.append(
            {
                "area": area,
                "weight": weight,
                "score_0_1": round(s, 4),
                "points": round(norm_pts, 2),
            }
        )
    weighted = raw_points * (100.0 / weight_sum)

    # Hard fail on critical codes
    hard = {
        "FIXTURE_ANSWER_USED",
        "RAW_CORPUS_EMPTY",
        "HALLUCINATED_FACT",
        "NO_COUNTER_EVIDENCE",
        "NO_UNKNOWNS",
        "NO_MONITORING_FRAMEWORK",
        "CONFIDENCE_UNJUSTIFIED",
        "PEER_ANALYSIS_MISSING",
    }
    hard_hit = sorted(codes & hard)
    passed = weighted >= float(IST02_PASS_SCORE) and not hard_hit
    # Spec: any listed failure code fails the exam
    if quality.get("failure_codes"):
        passed = False

    return {
        "scores_0_1": {k: round(v, 4) for k, v in scores.items()},
        "breakdown": breakdown,
        "weighted_total": round(weighted, 2),
        "max_total": 100.0,
        "pass_score": IST02_PASS_SCORE,
        "passed": passed,
        "hard_failure_codes": hard_hit,
        "failure_codes": list(quality.get("failure_codes") or []),
        "summary": (
            "PASS — raw-evidence institutional research validated"
            if passed
            else f"FAIL — score {round(weighted, 2)}/{IST02_PASS_SCORE}; codes={list(quality.get('failure_codes') or [])}"
        ),
    }
