"""IBS scoring — pass ≥ 85; normalize weights to 100."""

from __future__ import annotations

from typing import Any, Mapping

from institutional_benchmarks.schema import PASS_SCORE, REPORT_SECTIONS, RUBRIC_WEIGHTS


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def score_benchmark(
    report: Mapping[str, Any],
    quality: Mapping[str, Any],
    modules: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    sections = report.get("sections") or {}
    codes = set(quality.get("failure_codes") or [])

    struct_ratio = sum(1 for k in REPORT_SECTIONS if k in sections) / max(1, len(REPORT_SECTIONS))
    mod_hit = sum(
        1
        for m in ("FIRE-01", "FIRE-02", "FIRE-03", "FIRE-04", "FIRE-05", "FIRE-06", "CIO-01")
        if (modules.get(m) or {}).get("ok")
    )
    mod_ratio = mod_hit / 7.0
    evid_cov = float(quality.get("citation_coverage") or 0.0)
    contra_n = len((sections.get("evidence_contradicting") or {}).get("items") or [])
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
    writing = 0.2 if report.get("collapsed_to_buy_sell") else 1.0
    if "HALLUCINATED_FACT" in codes:
        writing = min(writing, 0.3)

    scores = {
        "research_structure": _clamp01(struct_ratio),
        "financial_reasoning": _clamp01(0.6 * (1.0 if sections.get("financial_analysis") else 0.0) + 0.4 * mod_ratio),
        "business_reasoning": _clamp01(
            0.5 * (1.0 if sections.get("business_quality") else 0.0)
            + 0.3 * (1.0 if sections.get("business_context") else 0.0)
            + 0.2 * mod_ratio
        ),
        "evidence_quality": _clamp01(0.5 * evid_cov + 0.3 * (1.0 if contra_n else 0.0) + 0.2 * cf_ok),
        "counter_evidence": _clamp01(min(1.0, contra_n / 2.0)),
        "confidence_calibration": _clamp01(conf_ok),
        "peer_comparison": _clamp01(peer_ok),
        "monitoring_framework": _clamp01(mon_ok),
        "source_traceability": _clamp01(0.7 * evid_cov + 0.3 * (0.0 if "PROVENANCE_MISSING" in codes else 1.0)),
        "institutional_writing_quality": _clamp01(
            0.5 * writing
            + 0.3 * (1.0 if sections.get("alternative_interpretations") else 0.0)
            + 0.2 * cf_ok
        ),
    }

    weight_sum = sum(float(w) for w in RUBRIC_WEIGHTS.values()) or 100.0
    raw_points = 0.0
    breakdown = []
    for area, weight in RUBRIC_WEIGHTS.items():
        s = float(scores.get(area) or 0.0)
        pts = s * float(weight)
        raw_points += pts
        breakdown.append(
            {
                "area": area,
                "weight": weight,
                "score_0_1": round(s, 4),
                "points": round(pts * (100.0 / weight_sum), 2),
            }
        )
    weighted = raw_points * (100.0 / weight_sum)

    passed = weighted >= float(PASS_SCORE) and not codes

    return {
        "scores_0_1": {k: round(v, 4) for k, v in scores.items()},
        "breakdown": breakdown,
        "weighted_total": round(weighted, 2),
        "max_total": 100.0,
        "pass_score": PASS_SCORE,
        "passed": passed,
        "failure_codes": list(codes),
        "summary": (
            "PASS — AGI institutional benchmark validated"
            if passed
            else f"FAIL — score {round(weighted, 2)}/{PASS_SCORE}; codes={sorted(codes)}"
        ),
    }
