"""Hypothesis Quality Score (HQS) — independent IEL metric for Phase 4.

Does NOT change CIO / overall pass weights.

v1.1.0 expands measurement for IHE:
  Coverage Quality · Support Quality · Conflict Handling · Ranking Quality ·
  Rejection Quality · Evaluation Quality · Confidence Quality

Deterministic only — no LLM grading.
"""

from __future__ import annotations

from typing import Any

HQS_VERSION = "hqs-v1.1.0"

# Component weights within HQS (sum = 1.0) — recorded independently in components{}
HQS_COMPONENT_WEIGHTS: dict[str, float] = {
    "plausibility": 0.10,
    "coverage_quality": 0.12,
    "support_quality": 0.12,
    "conflict_handling": 0.12,
    "ranking_quality": 0.12,
    "rejection_quality": 0.10,
    "evaluation_quality": 0.16,
    "confidence_quality": 0.16,
}


def _hyp_pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("hypothesis_generation") or {})


def _iew_pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("evidence_weighting") or {})


def _ihe_pack(probe: dict[str, Any]) -> dict[str, Any]:
    return dict(probe.get("hypothesis_evaluation") or {})


def _score_plausibility(pack: dict[str, Any]) -> tuple[float, str]:
    if pack.get("insufficient_evidence"):
        if str((pack.get("hypotheses") or [{}])[0].get("hypothesis") or "").lower().startswith(
            "insufficient"
        ):
            return 100.0, "insufficient_evidence_gate"
        return 40.0, "insufficient_without_gate_label"
    hyps = [h for h in (pack.get("hypotheses") or []) if isinstance(h, dict)]
    n = len(hyps)
    if n == 0:
        return 0.0, "no_hypotheses"
    if pack.get("fabricated") is True or pack.get("llm_used") is True:
        return 0.0, "fabricated_or_llm"
    if 2 <= n <= 5:
        base = 100.0
    elif n == 1:
        base = 55.0
    else:
        base = 70.0
    structured = all(h.get("hypothesis") and h.get("category") for h in hyps)
    if not structured:
        return base * 0.5, "missing_structure"
    return base, "ok"


def _score_coverage_quality(question: dict[str, Any], pack: dict[str, Any], ihe: dict[str, Any]) -> tuple[float, str]:
    if pack.get("insufficient_evidence"):
        return 85.0, "coverage_n_a_insufficient"
    # Family coverage (generation) + IHE coverage (evaluation)
    q = str(question.get("question") or "").lower()
    hyps = pack.get("hypotheses") or []
    keys = {str(h.get("template_key") or "") for h in hyps if isinstance(h, dict)}
    expected_keys: list[str] = []
    if "margin" in q:
        expected_keys = ["input_cost_inflation", "pricing_pressure", "demand_weakness"]
    elif "after earnings" in q or "stock fell" in q:
        expected_keys = ["guidance_disappointment", "valuation_rich", "margin_concern"]
    elif "premium" in q:
        expected_keys = ["higher_roe", "asset_quality", "deposit_franchise"]
    if expected_keys:
        family = round(100.0 * sum(1 for k in expected_keys if k in keys) / max(1, len(expected_keys)), 1)
    else:
        cats = {str(h.get("category")) for h in hyps if isinstance(h, dict)}
        family = 100.0 if len(cats) >= 2 or len(hyps) >= 2 else 60.0

    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    if evaluated:
        # Soft map IHE coverage (cap 16): prefer top viable hypothesis, not mean of rejects
        viable = [h for h in evaluated if h.get("status") != "Rejected"] or evaluated
        top = max(viable, key=lambda h: float(h.get("coverage_score") or 0))
        cov = float(top.get("coverage_score") or 0)
        # 0→50, 4→75, 8→100 (evidence sets are large; absolute fraction is naturally low)
        ihe_cov = round(min(100.0, 50.0 + (cov / 8.0) * 50.0), 1)
        score = round(0.55 * family + 0.45 * ihe_cov, 1)
        return score, f"family={family},ihe_cov={ihe_cov}"
    return family, "family_only"


def _score_support_quality(pack: dict[str, Any], ihe: dict[str, Any]) -> tuple[float, str]:
    if pack.get("insufficient_evidence"):
        return 100.0, "refused_to_invent"
    hyps = [h for h in (pack.get("hypotheses") or []) if isinstance(h, dict)]
    unsupported = [
        h
        for h in hyps
        if h.get("status") != "InsufficientEvidence" and not (h.get("supporting_evidence") or [])
    ]
    if unsupported:
        return 20.0, f"unsupported_count={len(unsupported)}"
    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    if evaluated:
        viable = [h for h in evaluated if h.get("status") != "Rejected"] or evaluated
        top = max(viable, key=lambda h: float(h.get("support_score") or 0))
        sup = float(top.get("support_score") or 0)
        # 0→55, 11→80, 22→100
        ihe_sup = round(min(100.0, 55.0 + (sup / 22.0) * 45.0), 1)
        return ihe_sup, "ihe_support_top_viable"
    return 100.0, "all_supported"


def _score_conflict_handling(pack: dict[str, Any], iew: dict[str, Any], ihe: dict[str, Any]) -> tuple[float, str]:
    if pack.get("insufficient_evidence"):
        return 90.0, "n_a_insufficient"
    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    if evaluated:
        # Conflict retained in evaluation_reason / contradicting_evidence
        retained = sum(1 for h in evaluated if h.get("contradicting_evidence") or float(h.get("conflict_raw") or 0) >= 0)
        explained = sum(1 for h in evaluated if "Conflict retained" in str(h.get("evaluation_reason") or ""))
        score = 70.0 + (15.0 if retained else 0) + (15.0 if explained else 0)
        return min(100.0, score), "ihe_conflict_retained"
    hyps = [h for h in (pack.get("hypotheses") or []) if isinstance(h, dict)]
    has_conflict = any(h.get("contradicting_evidence") for h in hyps)
    rejected = [h for h in hyps if h.get("status") == "Rejected"]
    score = 70.0
    if rejected and all((h.get("reason") or h.get("reject_reason")) for h in rejected):
        score += 15.0
    if has_conflict:
        score += 15.0
    elif iew.get("conflicts"):
        score -= 10.0
    else:
        score += 10.0
    return max(0.0, min(100.0, score)), "ihg_conflict"


def _score_ranking_quality(pack: dict[str, Any], ihe: dict[str, Any]) -> tuple[float, str]:
    if pack.get("forced_single_winner") is True or ihe.get("forced_single_winner") is True:
        return 40.0, "forced_single_winner_violation"
    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    if evaluated:
        ordered = sorted(evaluated, key=lambda h: -float(h.get("evaluation_score") or 0))
        # Status Preferred/Indeterminate/Plausible consistent with scores
        top = ordered[0]
        if ihe.get("outcome") == "preferred" and top.get("status") == "Preferred":
            return 100.0, "ihe_preferred_consistent"
        if ihe.get("outcome") in {"indeterminate", "plausible_set"} and ihe.get("plural"):
            return 95.0, "ihe_balanced_ranking"
        if top.get("status") in {"Preferred", "Plausible", "Indeterminate", "Rejected"}:
            return 85.0, "ihe_ranked"
        return 60.0, "ihe_status_odd"
    # IHG-only fallback
    hyps = [h for h in (pack.get("hypotheses") or []) if isinstance(h, dict)]
    if not hyps:
        return 75.0, "n_a"
    best = max(hyps, key=lambda h: float(h.get("overall_score") or 0))
    preferred = [h for h in hyps if h.get("status") in {"Preferred", "Contested"}]
    if pack.get("outcome") == "contested" and pack.get("plural"):
        return 100.0, "contested_plural"
    if preferred and preferred[0].get("hypothesis_id") == best.get("hypothesis_id"):
        return 100.0, "preferred_matches_strongest"
    if not preferred:
        return 75.0, "no_preferred"
    return 55.0, "preferred_misaligned"


def _score_rejection_quality(pack: dict[str, Any], ihe: dict[str, Any]) -> tuple[float, str]:
    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    pool = evaluated or [h for h in (pack.get("hypotheses") or []) if isinstance(h, dict)]
    rejected = [h for h in pool if h.get("status") == "Rejected"]
    if not rejected:
        return 90.0, "no_rejected"
    explained = all(
        (h.get("rejected_reason") or h.get("reason") or h.get("reject_reason") or h.get("evaluation_reason"))
        for h in rejected
    )
    # Must remain visible in the list (not deleted) — implied by presence in pool
    return (100.0 if explained else 40.0), f"rejected_explained={explained}"


def _score_evaluation_quality(ihe: dict[str, Any]) -> tuple[float, str]:
    if not ihe:
        return 70.0, "ihe_absent_neutral"
    if ihe.get("fabricated") or ihe.get("llm_used"):
        return 0.0, "fabricated_or_llm"
    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    report = ihe.get("report") or {}
    if ihe.get("outcome") == "insufficient_evidence":
        return 95.0, "insufficient_gate"
    if not evaluated:
        return 40.0, "no_evaluations"
    required_dims = (
        "support_score",
        "conflict_score",
        "coverage_score",
        "historical_score",
        "framework_score",
        "confidence",
        "evaluation_reason",
    )
    complete = all(all(h.get(d) is not None for d in required_dims) for h in evaluated)
    has_report = bool(report.get("evaluation_version") or report.get("evaluation_reason"))
    missing_ok = True
    # Missing evidence lists present (may be empty)
    for h in evaluated:
        if "missing_evidence" not in h:
            missing_ok = False
    score = 60.0
    if complete:
        score += 25.0
    if has_report:
        score += 10.0
    if missing_ok:
        score += 5.0
    if ihe.get("forced_single_winner") is False:
        score = min(100.0, score + 0.0)
    return min(100.0, score), "ihe_dimensions_complete" if complete else "ihe_incomplete"


def _score_confidence_quality(ihe: dict[str, Any], pack: dict[str, Any]) -> tuple[float, str]:
    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    if not evaluated:
        # IHG confidence present?
        hyps = [h for h in (pack.get("hypotheses") or []) if isinstance(h, dict)]
        if not hyps:
            return 80.0, "n_a"
        return 75.0, "ihg_only_confidence"
    # Critical missing must not have high confidence
    bad = 0
    for h in evaluated:
        missing = h.get("missing_evidence") or []
        critical = sum(1 for m in missing if isinstance(m, dict) and m.get("severity") == "high")
        conf = float(h.get("confidence") or 0)
        if critical and conf > 0.45:
            bad += 1
    if bad:
        return max(20.0, 70.0 - 15.0 * bad), f"overconfident_with_gaps={bad}"
    # Prefer moderate spread when plural/indeterminate
    if ihe.get("outcome") in {"indeterminate", "plausible_set"}:
        confs = [float(h.get("confidence") or 0) for h in evaluated if h.get("status") != "Rejected"]
        if confs and max(confs) < 0.9:
            return 100.0, "calibrated_plural"
        return 80.0, "plural_high_conf"
    return 90.0, "confidence_ok"


def judge_hypothesis_quality(question: dict[str, Any], probe: dict[str, Any]) -> dict[str, Any]:
    """Return HQS judgment. Independent of DIMENSION_WEIGHTS / CIO score."""
    pack = _hyp_pack(probe)
    iew = _iew_pack(probe)
    ihe = _ihe_pack(probe)

    if not pack:
        return {
            "dimension": "hypothesis_quality",
            "passed": True,
            "score": None,
            "hqs": None,
            "n_a": True,
            "hqs_version": HQS_VERSION,
            "independent_of_cio": True,
            "root_cause": None,
            "note": "hypothesis_generation absent from probe",
        }

    components: dict[str, Any] = {}
    mapping = {
        "plausibility": _score_plausibility(pack),
        "coverage_quality": _score_coverage_quality(question, pack, ihe),
        "support_quality": _score_support_quality(pack, ihe),
        "conflict_handling": _score_conflict_handling(pack, iew, ihe),
        "ranking_quality": _score_ranking_quality(pack, ihe),
        "rejection_quality": _score_rejection_quality(pack, ihe),
        "evaluation_quality": _score_evaluation_quality(ihe),
        "confidence_quality": _score_confidence_quality(ihe, pack),
    }
    for name, (score, note) in mapping.items():
        components[name] = {"score": score, "note": note}

    hqs = 0.0
    for name, w in HQS_COMPONENT_WEIGHTS.items():
        hqs += w * float(components[name]["score"])
    hqs = round(hqs, 2)
    passed = hqs >= 70.0

    root = None
    if not passed:
        worst = min(components.items(), key=lambda kv: float(kv[1]["score"]))
        root = f"hqs_weak_{worst[0]}"

    return {
        "dimension": "hypothesis_quality",
        "passed": passed,
        "score": hqs,
        "hqs": hqs,
        "components": components,
        "component_weights": dict(HQS_COMPONENT_WEIGHTS),
        "n_hypotheses": pack.get("n_hypotheses"),
        "outcome": (ihe.get("outcome") if ihe else None) or pack.get("outcome"),
        "ihe_outcome": ihe.get("outcome") if ihe else None,
        "plural": (ihe.get("plural") if ihe else None) if ihe else pack.get("plural"),
        "forced_single_winner": bool(pack.get("forced_single_winner") or ihe.get("forced_single_winner")),
        "insufficient_evidence": bool(pack.get("insufficient_evidence")),
        "hqs_version": HQS_VERSION,
        "independent_of_cio": True,
        "n_a": False,
        "root_cause": root,
    }


def aggregate_hqs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Suite-level HQS summary from scored rows."""
    scores: list[float] = []
    n_na = 0
    n_pass = 0
    n_fail = 0
    outcomes: dict[str, int] = {}
    component_sums: dict[str, list[float]] = {k: [] for k in HQS_COMPONENT_WEIGHTS}
    for r in rows:
        j = ((r.get("dimensions") or {}).get("hypothesis_quality")) or r.get("hypothesis_quality") or {}
        if j.get("n_a") or (j.get("hqs") is None and j.get("score") is None):
            n_na += 1
            continue
        s = j.get("hqs")
        if s is None:
            s = j.get("score")
        if s is None:
            n_na += 1
            continue
        scores.append(float(s))
        if j.get("passed"):
            n_pass += 1
        else:
            n_fail += 1
        oc = str(j.get("ihe_outcome") or j.get("outcome") or "unknown")
        outcomes[oc] = outcomes.get(oc, 0) + 1
        comps = j.get("components") or {}
        for k in HQS_COMPONENT_WEIGHTS:
            if k in comps and comps[k].get("score") is not None:
                component_sums[k].append(float(comps[k]["score"]))
    n = len(scores)
    component_means = {
        k: round(sum(v) / len(v), 2) if v else None for k, v in component_sums.items()
    }
    return {
        "hqs_version": HQS_VERSION,
        "independent_of_cio": True,
        "n_scored": n,
        "n_na": n_na,
        "mean_hqs": round(sum(scores) / n, 2) if n else None,
        "pass_pct": round(100.0 * n_pass / n, 2) if n else None,
        "passed": n_pass,
        "failed": n_fail,
        "outcomes": outcomes,
        "component_means": component_means,
        "note": "HQS does not affect IEL overall / CIO score weights",
    }
