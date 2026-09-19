"""Deterministic Institutional Confidence Calibration engine.

Confidence is an emergent property of IEW → IHG → IHE → ICR.
Never manually assigned. Never raised by an LLM. Fixtures never increase it.
"""

from __future__ import annotations

from typing import Any

from institutional_confidence_calibration.schema import (
    CONFIDENCE_VERSION,
    DIMENSION_WEIGHTS,
    FREEZE_LOCKS,
    ICC_VERSION,
    LEVEL_BANDS,
)


def _round(x: float, n: int = 2) -> float:
    return round(float(x), n)


def _clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(x)))


def _level(score: float) -> str:
    s = int(round(score))
    for threshold, label in LEVEL_BANDS:
        if s >= threshold:
            return label
    return "Very Low"


def _viable_ihe(ihe: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for h in ihe.get("evaluated_hypotheses") or []:
        if not isinstance(h, dict):
            continue
        if h.get("status") in {"Rejected", "InsufficientEvidence"}:
            continue
        out.append(h)
    return out


def _evidence_quality(iew: dict[str, Any]) -> tuple[float, str]:
    ordered = [e for e in (iew.get("ordered_evidence") or iew.get("top_weighted") or []) if isinstance(e, dict)]
    if not ordered:
        n_elig = int(iew.get("n_eligible") or 0)
        if n_elig == 0:
            return 25.0, "no eligible weighted evidence"
        return 45.0, "eligible evidence present without ordered scores"
    scores = [float(e.get("weight_score") or e.get("quality_score") or 0) for e in ordered[:8]]
    # IEW weight_score typically ~0–40; map mean to 0–100
    mean_w = sum(scores) / max(1, len(scores))
    mapped = _clip(30.0 + (mean_w / 28.0) * 70.0)
    return _round(mapped), f"mean weighted evidence score {mean_w:.1f}"


def _coverage(ihe: dict[str, Any], iew: dict[str, Any]) -> tuple[float, str]:
    viable = _viable_ihe(ihe)
    if not viable:
        if ihe.get("outcome") == "insufficient_evidence":
            return 20.0, "insufficient evidence after evaluation"
        return 35.0, "no viable evaluated hypotheses"
    top = max(viable, key=lambda h: float(h.get("coverage_score") or 0))
    cov = float(top.get("coverage_score") or 0)
    # IHE coverage capped ~16
    mapped = _clip(40.0 + (cov / 12.0) * 60.0)
    n_elig = int(iew.get("n_eligible") or 0)
    if n_elig >= 5:
        mapped = min(100.0, mapped + 5.0)
    return _round(mapped), f"top coverage_score={cov:g}"


def _hypothesis_strength(ihe: dict[str, Any]) -> tuple[float, str, dict[str, Any] | None]:
    viable = _viable_ihe(ihe)
    if not viable:
        return 20.0, "no preferred or viable hypothesis", None
    preferred = next((h for h in viable if h.get("preferred") or h.get("status") == "Preferred"), None)
    top = preferred or max(viable, key=lambda h: float(h.get("evaluation_score") or 0))
    score = float(top.get("evaluation_score") or 0)
    mapped = _clip(score)  # already ~0–100
    return _round(mapped), f"preferred evaluation_score={score:g}", top


def _hypothesis_separation(ihe: dict[str, Any], preferred: dict[str, Any] | None) -> tuple[float, str]:
    viable = _viable_ihe(ihe)
    if not preferred or len(viable) < 2:
        if preferred:
            return 70.0, "single viable hypothesis — separation not contested"
        return 25.0, "cannot measure separation"
    ordered = sorted(viable, key=lambda h: -float(h.get("evaluation_score") or 0))
    gap = float(ordered[0].get("evaluation_score") or 0) - float(ordered[1].get("evaluation_score") or 0)
    # Clear lead ≥12 → high; balanced ≤4 → low
    if gap >= 12:
        mapped = 95.0
    elif gap >= 8:
        mapped = 80.0
    elif gap >= 4:
        mapped = 60.0
    else:
        mapped = 40.0
    return _round(mapped), f"evaluation gap={gap:g}"


def _conflict(ihe: dict[str, Any], iew: dict[str, Any]) -> tuple[float, str]:
    """Return inverted conflict score: high = low unresolved conflict (good for confidence)."""
    viable = _viable_ihe(ihe)
    conflict_raw = 0.0
    if viable:
        top = max(viable, key=lambda h: float(h.get("evaluation_score") or 0))
        conflict_raw = float(top.get("conflict_raw") or top.get("conflict_score") or 0)
    n_conflicts = int(iew.get("n_conflicts") or len(iew.get("conflicts") or []))
    # Map raw conflict to penalty-friendly inverted score
    # conflict_raw often 0–40; conflict_score in IHE is inverted already sometimes
    pressure = conflict_raw + 5.0 * n_conflicts
    mapped = _clip(100.0 - min(80.0, pressure * 1.8))
    return _round(mapped), f"conflict_raw={conflict_raw:g}, n_iew_conflicts={n_conflicts}"


def _committee_agreement(icr: dict[str, Any]) -> tuple[float, str]:
    report = icr.get("report") or {}
    if report.get("outcome") == "insufficient_evidence" or int(icr.get("n_cases") or 0) == 0:
        return 30.0, "no committee cases to agree on"
    dist = icr.get("probability_distribution") or report.get("probability_distribution") or {}
    if not dist:
        return 40.0, "missing probability distribution"
    vals = [float(v) for v in dist.values()]
    top = max(vals) if vals else 0.0
    n = len(vals)
    disagreements = len(report.get("key_disagreements") or [])
    # High modal probability → agreement; many disagreements → lower
    if n == 1:
        mapped = 88.0
        note = "single evidence-backed case"
    else:
        # 100% → 100; 55% modal with 3 cases → ~70; 40% → ~50
        mapped = _clip(35.0 + top * 0.65)
        mapped = _clip(mapped - 8.0 * min(3, disagreements))
        note = f"modal probability={top:g}%, disagreements={disagreements}"
    return _round(mapped), note


def _historical(im: dict[str, Any], ihe: dict[str, Any]) -> tuple[float, str]:
    viable = _viable_ihe(ihe)
    hist = 0.0
    if viable:
        top = max(viable, key=lambda h: float(h.get("historical_score") or 0))
        hist = float(top.get("historical_score") or 0)
    # IHE historical often 0–12
    mapped = _clip(35.0 + (hist / 10.0) * 55.0)
    if im.get("have_we_seen_this_before"):
        mapped = min(100.0, mapped + 10.0)
        n_mem = len(im.get("top_memory_ids") or [])
        note = f"analogues present (n={n_mem}), historical_score={hist:g}"
    else:
        mapped = min(mapped, 65.0)
        note = f"no strong analogue match; historical_score={hist:g}"
    return _round(mapped), note


def _framework(fs: dict[str, Any], ihe: dict[str, Any], preferred: dict[str, Any] | None) -> tuple[float, str]:
    fids = list(fs.get("framework_ids") or [])
    if not fids:
        return 55.0, "no frameworks selected"
    if preferred:
        fw_score = float(preferred.get("framework_score") or 0)
        mapped = _clip(45.0 + (fw_score / 10.0) * 55.0)
        aligned = True
        hyp_fw = str(preferred.get("framework") or "")
        if hyp_fw and not any(hyp_fw.upper() in f.upper() or f.upper() in hyp_fw.upper() for f in fids):
            mapped = min(mapped, 50.0)
            aligned = False
        return _round(mapped), f"framework_score={fw_score:g}, aligned={aligned}"
    return 50.0, "frameworks selected without preferred hypothesis"


def _missing_penalty(ihe: dict[str, Any], icr: dict[str, Any]) -> tuple[float, list[Any], str]:
    """Return penalty points (0–40), missing items, note."""
    items: list[Any] = []
    for h in ihe.get("evaluated_hypotheses") or []:
        if isinstance(h, dict):
            for m in h.get("missing_evidence") or []:
                items.append(m)
    for m in (icr.get("report") or {}).get("missing_evidence") or []:
        items.append(m)
    # Dedup
    seen = set()
    uniq = []
    for m in items:
        key = str(m.get("item") if isinstance(m, dict) else m).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    high = sum(
        1
        for m in uniq
        if isinstance(m, dict) and str(m.get("severity") or "").lower() in {"high", "critical"}
    )
    penalty = min(40.0, 6.0 * len(uniq) + 4.0 * high)
    return _round(penalty), uniq[:12], f"missing_n={len(uniq)}, high={high}"


def _integrity(
    temporal: dict[str, Any] | None,
    replay_ok: bool | None,
    as_of: str | None,
) -> tuple[float, bool, bool, str]:
    """Temporal + replay must be TRUE for full integrity contribution."""
    t = temporal or {}
    # Soft probe shape: {pre_analog, post_analog}; pipeline may pass report flags
    temporal_ok = True
    if "temporal_ok" in t:
        temporal_ok = bool(t.get("temporal_ok"))
    elif t.get("rejected") is True or t.get("leakage") is True:
        temporal_ok = False
    elif t.get("pre_analog") or t.get("post_analog"):
        for key in ("pre_analog", "post_analog"):
            rep = t.get(key) or {}
            if isinstance(rep, dict) and (rep.get("rejected") or rep.get("status") == "rejected"):
                temporal_ok = False

    if replay_ok is None:
        # Default true for soft live; as_of replay still expected clean
        replay_ok = True
    integrity = 100.0 if (temporal_ok and replay_ok) else 0.0
    note = f"temporal={temporal_ok}, replay={replay_ok}"
    if as_of and not replay_ok:
        note += ", as_of replay uncertainty"
    return integrity, temporal_ok, bool(replay_ok), note


def _fixture_penalty(metadata: dict[str, Any] | None, iew: dict[str, Any]) -> tuple[float, str]:
    """Fixtures never increase confidence — apply penalty when fixture-dependent."""
    meta = metadata or {}
    fixture = bool(meta.get("fixture_dependence") or meta.get("fixture") or iew.get("fixture_dependence"))
    if fixture:
        return 12.0, "fixture dependence penalty (fixtures never raise confidence)"
    return 0.0, "no fixture dependence"


def calibrate(
    *,
    question: str,
    evidence_weighting: dict[str, Any] | None = None,
    hypothesis_generation: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    temporal_integrity: dict[str, Any] | None = None,
    replay_integrity: bool | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute InstitutionalConfidenceReport from the judgment stack."""
    iew = evidence_weighting or {}
    ihg = hypothesis_generation or {}
    ihe = hypothesis_evaluation or {}
    icr = committee_reasoning or {}
    im = institutional_memory or {}
    fs = framework_selection or {}

    eq, eq_n = _evidence_quality(iew)
    cov, cov_n = _coverage(ihe, iew)
    hyp_s, hyp_n, preferred = _hypothesis_strength(ihe)
    sep, sep_n = _hypothesis_separation(ihe, preferred)
    conf_inv, conf_n = _conflict(ihe, iew)
    agr, agr_n = _committee_agreement(icr)
    hist, hist_n = _historical(im, ihe)
    fw, fw_n = _framework(fs, ihe, preferred)
    miss_pen, missing_items, miss_n = _missing_penalty(ihe, icr)
    integ, temporal_ok, replay_ok, integ_n = _integrity(temporal_integrity, replay_integrity, as_of)
    fix_pen, fix_n = _fixture_penalty(metadata, iew)

    # Disagreement / weak analogue / poor coverage extra soft penalties already in dims;
    # explicit additive penalties:
    disagreement_pen = 0.0
    n_dis = len((icr.get("report") or {}).get("key_disagreements") or [])
    if n_dis >= 2:
        disagreement_pen = 5.0 * min(3, n_dis - 1)

    components = {
        "evidence_quality": {"score": eq, "note": eq_n},
        "coverage_score": {"score": cov, "note": cov_n},
        "hypothesis_strength": {"score": hyp_s, "note": hyp_n},
        "hypothesis_separation": {"score": sep, "note": sep_n},
        "conflict_score": {"score": conf_inv, "note": conf_n},
        "committee_agreement": {"score": agr, "note": agr_n},
        "historical_score": {"score": hist, "note": hist_n},
        "framework_consistency": {"score": fw, "note": fw_n},
        "integrity_gate": {"score": integ, "note": integ_n},
    }

    weighted = 0.0
    for k, w in DIMENSION_WEIGHTS.items():
        weighted += w * float(components[k]["score"])

    total_penalty = miss_pen + fix_pen + disagreement_pen
    if not temporal_ok or not replay_ok:
        total_penalty = max(total_penalty, 25.0)

    overall = _clip(_round(weighted - total_penalty))
    level = _level(overall)

    # Build explanation
    ranked = sorted(components.items(), key=lambda kv: -float(kv[1]["score"]))
    raisers = [f"{k.replace('_', ' ')} ({kv['score']:.0f}/100 — {kv['note']})" for k, kv in ranked[:3] if kv["score"] >= 70]
    lowerers = [f"{k.replace('_', ' ')} ({kv['score']:.0f}/100 — {kv['note']})" for k, kv in ranked if kv["score"] < 55]
    if miss_pen > 0:
        lowerers.append(f"missing evidence penalty −{miss_pen:g} ({miss_n})")
    if disagreement_pen > 0:
        lowerers.append(f"committee disagreement penalty −{disagreement_pen:g}")
    if fix_pen > 0:
        lowerers.append(fix_n)
    if not temporal_ok or not replay_ok:
        lowerers.append("integrity gate failed — temporal/replay uncertainty")

    what_would_raise = []
    for m in missing_items[:5]:
        item = m.get("item") if isinstance(m, dict) else m
        what_would_raise.append(str(item))
    if not what_would_raise and lowerers:
        what_would_raise.append("Stronger preferred-hypothesis separation and lower unresolved conflict")

    unresolved_conflicts = []
    for c in (iew.get("conflicts") or [])[:5]:
        if isinstance(c, dict):
            unresolved_conflicts.append(c)
    for h in _viable_ihe(ihe)[:1]:
        for e in (h.get("contradicting_evidence") or [])[:3]:
            unresolved_conflicts.append({"evidence_id": e, "role": "contradicting"})

    reason = (
        f"Confidence: {int(round(overall))}/100 ({level}) because "
    )
    if raisers:
        reason += "strengths include " + "; ".join(raisers[:2])
    else:
        reason += "the judgment stack provides limited positive support"
    if lowerers:
        reason += ". Confidence reduced by " + "; ".join(lowerers[:3])
    if what_would_raise:
        reason += ". Additional evidence that would raise confidence: " + "; ".join(what_would_raise[:3])
    reason += "."

    report = {
        "overall_confidence": int(round(overall)),
        "confidence_level": level,
        "evidence_quality": _round(eq),
        "coverage_score": _round(cov),
        "hypothesis_strength": _round(hyp_s),
        "hypothesis_separation": _round(sep),
        "conflict_score": _round(conf_inv),
        "committee_agreement": _round(agr),
        "historical_score": _round(hist),
        "framework_consistency": _round(fw),
        "missing_evidence_penalty": _round(miss_pen),
        "temporal_integrity": temporal_ok,
        "replay_integrity": replay_ok,
        "confidence_reason": reason,
        "confidence_version": CONFIDENCE_VERSION,
        "why_increased": raisers,
        "why_decreased": lowerers,
        "evidence_reducing_confidence": unresolved_conflicts[:8],
        "missing_evidence_that_would_raise": what_would_raise[:8],
        "unresolved_conflicting_evidence": unresolved_conflicts[:8],
        "penalties": {
            "missing_evidence": miss_pen,
            "fixture_dependence": fix_pen,
            "committee_disagreement": disagreement_pen,
            "total": _round(total_penalty),
        },
        "components": components,
        "dimension_weights": dict(DIMENSION_WEIGHTS),
        "preferred_hypothesis_id": (preferred or {}).get("hypothesis_id"),
        "icr_preferred_case": icr.get("preferred_case"),
        "question": question,
        "llm_used": False,
        "manually_assigned": False,
        "fixture_raised_confidence": False,
        "fabricated": False,
        "deterministic": True,
    }

    return {
        "icc_version": ICC_VERSION,
        "confidence_version": CONFIDENCE_VERSION,
        "question": question,
        "as_of": as_of,
        "report": report,
        "overall_confidence": report["overall_confidence"],
        "confidence_level": level,
        "confidence_reason": reason,
        "guides_confidence": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "icr_changed": False,
        "ihe_changed": False,
        "ihg_changed": False,
        "iew_changed": False,
        "llm_used": False,
        "manually_assigned": False,
        "fabricated": False,
        "deterministic": True,
        "freeze_locks": dict(FREEZE_LOCKS),
        "metadata": dict(metadata or {}),
    }
