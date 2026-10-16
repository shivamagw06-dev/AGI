"""Deterministic multi-dimension hypothesis evaluation (no LLM)."""

from __future__ import annotations

import re
from typing import Any

from institutional_hypothesis_evaluation.schema import (
    BALANCED_GAP,
    CLEAR_LEAD_GAP,
    DIMENSION_CAPS,
    EVALUATION_VERSION,
    IHE_VERSION,
    MIN_CONFIDENCE_WITH_CRITICAL_MISSING,
    REJECT_BELOW,
)


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _round(x: float) -> float:
    return round(float(x), 2)


def _hypotheses(ihg: dict[str, Any]) -> list[dict[str, Any]]:
    return [h for h in (ihg.get("hypotheses") or []) if isinstance(h, dict)]


def _eligible_evidence(iew: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(iew.get("weighted_evidence") or iew.get("ordered_evidence") or [])
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        if r.get("eligible") is False:
            continue
        out.append(r)
    return out


def _evidence_by_id(evidence: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(e.get("evidence_id")): e for e in evidence if e.get("evidence_id")}


def _memory_blob(im: dict[str, Any]) -> str:
    parts = [
        im.get("surface_bullets"),
        im.get("comparison"),
        im.get("regimes"),
        [m.get("title") for m in (im.get("memories") or []) if isinstance(m, dict)],
        [m.get("lessons_learned") for m in (im.get("memories") or []) if isinstance(m, dict)],
    ]
    return _norm(parts)


def _framework_ids(fs: dict[str, Any] | None, framework_ids: list[str] | None) -> list[str]:
    if framework_ids:
        return [str(x) for x in framework_ids]
    fs = fs or {}
    return [str(x) for x in (fs.get("framework_ids") or [])]


def _missing_list(
    *,
    hyp: dict[str, Any],
    playbook: dict[str, Any] | None,
    evidence_graph: dict[str, Any] | None,
    support_ids: set[str],
) -> list[dict[str, Any]]:
    """Critical gaps that would most improve certainty — never invent facts."""
    missing: list[dict[str, Any]] = []
    pb = playbook or {}
    eg = evidence_graph or {}
    required = list(pb.get("evidence_required") or []) + list(eg.get("missing_evidence_required") or [])
    support_blob = _norm(" ".join(support_ids) + " " + str(hyp.get("hypothesis") or ""))
    for req in required[:12]:
        token = _norm(req)
        if not token:
            continue
        if token not in support_blob and not any(t in support_blob for t in token.split() if len(t) > 4):
            missing.append(
                {
                    "item": str(req),
                    "severity": "high" if any(k in token for k in ("audit", "cash", "filing", "npa", "guidance")) else "medium",
                    "why": "Listed as required by playbook/graph but not linked in supporting evidence",
                    "would_improve": "Raise coverage and confidence if obtained",
                }
            )
    # Structural gap: support but zero conflict check when competitors exist is OK;
    # if support is thin, ask for primary filing
    if float(hyp.get("support_score") or hyp.get("weighted_support") or 0) < 25:
        missing.append(
            {
                "item": "Primary company filing or audited disclosure confirming the mechanism",
                "severity": "high",
                "why": "Support score is thin for a preferred institutional explanation",
                "would_improve": "Materially raise support_score and confidence",
            }
        )
    # Deduplicate by item text
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for m in missing:
        k = _norm(m.get("item"))
        if k in seen:
            continue
        seen.add(k)
        out.append(m)
    return out[:8]


def evaluate_one(
    hyp: dict[str, Any],
    *,
    eligible: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    peers: list[dict[str, Any]],
    institutional_memory: dict[str, Any] | None,
    framework_ids: list[str],
    playbook: dict[str, Any] | None,
    evidence_graph: dict[str, Any] | None,
) -> dict[str, Any]:
    caps = DIMENSION_CAPS
    support_raw = float(hyp.get("support_score") or hyp.get("weighted_support") or 0.0)
    conflict_raw = float(hyp.get("conflict_score") or hyp.get("weighted_conflict") or 0.0)
    support_ids = {str(x) for x in (hyp.get("supporting_evidence") or []) if x}
    conflict_ids = {str(x) for x in (hyp.get("contradicting_evidence") or []) if x}

    # --- Support (0..cap) normalised vs 100 weight units ---
    support_score = _round(min(float(caps["support"]), support_raw * float(caps["support"]) / 100.0))

    # --- Conflict (inverted): more conflict → lower score; retain visibility ---
    conflict_burden = min(1.0, conflict_raw / 80.0)
    conflict_score = _round(float(caps["conflict"]) * (1.0 - conflict_burden))

    # --- Coverage: share of eligible evidence weight touched by this hyp ---
    total_w = sum(float(e.get("weight_score") or 0) for e in eligible) or 1.0
    touched_ids = support_ids | conflict_ids
    touched_w = sum(float(by_id[i].get("weight_score") or 0) for i in touched_ids if i in by_id)
    coverage_frac = min(1.0, touched_w / total_w)
    # Also credit fraction of eligible count linked
    if eligible:
        coverage_frac = max(coverage_frac, min(1.0, len(touched_ids) / max(1, len(eligible))))
    coverage_score = _round(float(caps["coverage"]) * coverage_frac)

    # --- Historical consistency (IMAI) ---
    mem_blob = _memory_blob(institutional_memory or {})
    hyp_blob = _norm(hyp.get("hypothesis"))
    hist = 0.35
    if (institutional_memory or {}).get("have_we_seen_this_before"):
        hist = 0.55
    # Token overlap with memory surfaces
    tokens = [t for t in re.findall(r"[a-z]{4,}", hyp_blob) if t not in {"that", "with", "from", "this"}]
    hits = sum(1 for t in tokens[:12] if t in mem_blob)
    if tokens:
        hist = max(hist, min(1.0, 0.4 + 0.6 * (hits / max(1, min(8, len(tokens))))))
    if not mem_blob:
        hist = 0.45  # neutral when no memory
    historical_score = _round(float(caps["historical"]) * hist)

    # --- Framework consistency (consume, never modify) ---
    hyp_fw = str(hyp.get("framework") or "")
    fw_ok = 0.4
    if not framework_ids:
        fw_ok = 0.7
    elif hyp_fw:
        fw_blob = " ".join(framework_ids).upper()
        if hyp_fw.upper() in fw_blob or any(hyp_fw.upper() in f.upper() or f.upper() in hyp_fw.upper() for f in framework_ids):
            fw_ok = 1.0
        else:
            # Family overlap FW_X_Y
            fam = hyp_fw.split("_")[1] if "_" in hyp_fw else hyp_fw
            fw_ok = 0.75 if fam and fam.upper() in fw_blob else 0.35
    framework_score = _round(float(caps["framework"]) * fw_ok)

    # --- Missing evidence (inverted) ---
    missing = _missing_list(
        hyp=hyp,
        playbook=playbook,
        evidence_graph=evidence_graph,
        support_ids=support_ids,
    )
    critical = sum(1 for m in missing if m.get("severity") == "high")
    miss_penalty = min(1.0, 0.25 * len(missing) + 0.2 * critical)
    missing_evidence_score = _round(float(caps["missing_evidence"]) * (1.0 - miss_penalty))

    # --- Alternative strength (inverted): strong peers hurt uniqueness ---
    peer_scores = [
        float(p.get("support_score") or p.get("weighted_support") or 0)
        for p in peers
        if p.get("hypothesis_id") != hyp.get("hypothesis_id")
        and p.get("status") not in {"InsufficientEvidence"}
    ]
    best_alt = max(peer_scores) if peer_scores else 0.0
    alt_frac = min(1.0, best_alt / max(support_raw, 1.0)) if support_raw > 0 else (1.0 if best_alt > 0 else 0.0)
    alternative_strength_score = _round(float(caps["alternative_strength"]) * (1.0 - 0.85 * alt_frac))

    # --- Explanatory power: high support, low conflict burden, coverage, low missing ---
    exp = (
        0.35 * min(1.0, support_raw / 80.0)
        + 0.25 * (1.0 - conflict_burden)
        + 0.25 * coverage_frac
        + 0.15 * (1.0 - miss_penalty)
    )
    explanatory_power_score = _round(float(caps["explanatory_power"]) * min(1.0, exp))

    breakdown = {
        "support": support_score,
        "conflict": conflict_score,
        "coverage": coverage_score,
        "historical": historical_score,
        "framework": framework_score,
        "missing_evidence": missing_evidence_score,
        "alternative_strength": alternative_strength_score,
        "explanatory_power": explanatory_power_score,
    }
    evaluation_score = _round(sum(breakdown.values()))

    # Confidence: shrink with conflict + critical missing; never inflate when gaps
    conf = min(0.95, max(0.05, evaluation_score / 100.0))
    conf *= 1.0 - 0.35 * conflict_burden
    if critical:
        conf = min(conf, MIN_CONFIDENCE_WITH_CRITICAL_MISSING)
        conf *= 1.0 - 0.08 * critical
    conf = _round(conf)

    citations = []
    for eid in list(support_ids)[:5]:
        e = by_id.get(eid) or {"evidence_id": eid}
        citations.append(
            {
                "evidence_id": eid,
                "role": "support",
                "weight_score": e.get("weight_score"),
                "source": e.get("source"),
                "title": e.get("title"),
            }
        )
    for eid in list(conflict_ids)[:5]:
        e = by_id.get(eid) or {"evidence_id": eid}
        citations.append(
            {
                "evidence_id": eid,
                "role": "conflict",
                "weight_score": e.get("weight_score"),
                "source": e.get("source"),
                "title": e.get("title"),
            }
        )

    reason = (
        f"Support {support_score:g}/{caps['support']:g} (raw {support_raw:g}); "
        f"Conflict retained {conflict_raw:g} → score {conflict_score:g}/{caps['conflict']:g}; "
        f"Coverage {coverage_score:g}; Historical {historical_score:g}; "
        f"Framework {framework_score:g}; Missing-evidence score {missing_evidence_score:g} "
        f"({len(missing)} gaps, {critical} critical); "
        f"Alt-strength {alternative_strength_score:g}; Explanatory {explanatory_power_score:g}. "
        f"Evaluation total {evaluation_score:g}."
    )

    return {
        "hypothesis_id": hyp.get("hypothesis_id"),
        "hypothesis": hyp.get("hypothesis"),
        "category": hyp.get("category"),
        "framework": hyp.get("framework"),
        "template_key": hyp.get("template_key"),
        "ihg_status": hyp.get("status"),
        "ihg_share": hyp.get("share"),
        "support_score": support_score,
        "conflict_score": conflict_score,
        "conflict_raw": conflict_raw,
        "coverage_score": coverage_score,
        "historical_score": historical_score,
        "framework_score": framework_score,
        "missing_evidence_score": missing_evidence_score,
        "alternative_strength_score": alternative_strength_score,
        "explanatory_power_score": explanatory_power_score,
        "evaluation_score": evaluation_score,
        "evaluation_breakdown": breakdown,
        "confidence": conf,
        "missing_evidence": missing,
        "supporting_evidence": list(support_ids),
        "contradicting_evidence": list(conflict_ids),
        "citations": citations,
        "evaluation_reason": reason,
        "evaluation_version": EVALUATION_VERSION,
        "ihe_version": IHE_VERSION,
        "status": None,  # assigned later
        "preferred": False,
        "rejected_reason": None,
        "fabricated": False,
        "llm_used": False,
        "deterministic": True,
    }


def _assign_statuses(evaluated: list[dict[str, Any]], *, insufficient: bool) -> dict[str, Any]:
    if insufficient or not evaluated:
        return {
            "outcome": "insufficient_evidence",
            "preferred_hypothesis": None,
            "alternative_hypotheses": [],
            "plural": False,
            "forced_single_winner": False,
            "evaluated": evaluated,
        }

    ordered = sorted(
        evaluated,
        key=lambda h: (
            -float(h.get("evaluation_score") or 0),
            -float(h.get("support_score") or 0),
            str(h.get("hypothesis_id") or ""),
        ),
    )

    for h in ordered:
        score = float(h.get("evaluation_score") or 0)
        if score < REJECT_BELOW:
            h["status"] = "Rejected"
            h["rejected_reason"] = (
                f"Evaluation score {score:g} below reject threshold {REJECT_BELOW:g}; "
                "retained for inspection with conflicts and missing evidence visible."
            )
            h["preferred"] = False
        else:
            h["status"] = "Plausible"
            h["preferred"] = False

    viable = [h for h in ordered if h.get("status") != "Rejected"]
    if not viable:
        return {
            "outcome": "rejected_all",
            "preferred_hypothesis": None,
            "alternative_hypotheses": ordered,
            "plural": True,
            "forced_single_winner": False,
            "evaluated": ordered,
        }

    top = viable[0]
    second = viable[1] if len(viable) > 1 else None
    gap = float(top.get("evaluation_score") or 0) - float((second or {}).get("evaluation_score") or 0)

    if second is None or gap >= CLEAR_LEAD_GAP:
        top["status"] = "Preferred"
        top["preferred"] = True
        top["evaluation_reason"] = (top.get("evaluation_reason") or "") + (
            f" | Preferred: lead of {gap:g} evaluation points over next viable hypothesis."
        )
        alts = [h for h in ordered if h.get("hypothesis_id") != top.get("hypothesis_id")]
        return {
            "outcome": "preferred",
            "preferred_hypothesis": top,
            "alternative_hypotheses": alts,
            "plural": bool(alts),
            "forced_single_winner": False,
            "evaluated": ordered,
        }

    # Balanced — do not force a winner
    if gap <= BALANCED_GAP:
        for h in viable:
            if abs(float(h.get("evaluation_score") or 0) - float(top.get("evaluation_score") or 0)) <= BALANCED_GAP:
                h["status"] = "Indeterminate"
                h["evaluation_reason"] = (h.get("evaluation_reason") or "") + (
                    " | Indeterminate: evidence supports multiple viable explanations; "
                    "no forced single winner."
                )
        return {
            "outcome": "indeterminate",
            "preferred_hypothesis": None,
            "alternative_hypotheses": ordered,
            "plural": True,
            "forced_single_winner": False,
            "evaluated": ordered,
        }

    # Moderate gap — plausible set (top cluster)
    for h in viable:
        if abs(float(h.get("evaluation_score") or 0) - float(top.get("evaluation_score") or 0)) <= CLEAR_LEAD_GAP:
            h["status"] = "Plausible"
            h["evaluation_reason"] = (h.get("evaluation_reason") or "") + (
                " | Plausible: competitive with the leader; retained as alternative."
            )
    return {
        "outcome": "plausible_set",
        "preferred_hypothesis": None,
        "alternative_hypotheses": ordered,
        "plural": True,
        "forced_single_winner": False,
        "evaluated": ordered,
    }


def evaluate_hypotheses(
    *,
    question: str,
    hypothesis_generation: dict[str, Any] | None = None,
    evidence_weighting: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    framework_ids: list[str] | None = None,
    playbook_selection: dict[str, Any] | None = None,
    evidence_graph: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate IHG hypotheses with IEW weights + memory/framework/missing dimensions."""
    ihg = hypothesis_generation or {}
    iew = evidence_weighting or {}
    hyps = _hypotheses(ihg)
    eligible = _eligible_evidence(iew)
    by_id = _evidence_by_id(eligible)
    fids = _framework_ids(framework_selection, framework_ids)

    insufficient = bool(ihg.get("insufficient_evidence")) or (
        len(hyps) == 1 and str(hyps[0].get("status")) == "InsufficientEvidence"
    )

    evaluated: list[dict[str, Any]] = []
    if not insufficient:
        for h in hyps:
            if h.get("status") == "InsufficientEvidence":
                continue
            evaluated.append(
                evaluate_one(
                    h,
                    eligible=eligible,
                    by_id=by_id,
                    peers=hyps,
                    institutional_memory=institutional_memory,
                    framework_ids=fids,
                    playbook=playbook_selection,
                    evidence_graph=evidence_graph,
                )
            )

    assigned = _assign_statuses(evaluated, insufficient=insufficient)
    ordered = assigned["evaluated"]
    preferred = assigned["preferred_hypothesis"]

    # Aggregate report object
    report = {
        "preferred_hypothesis": (
            {
                "hypothesis_id": preferred.get("hypothesis_id"),
                "hypothesis": preferred.get("hypothesis"),
                "status": preferred.get("status"),
                "evaluation_score": preferred.get("evaluation_score"),
                "confidence": preferred.get("confidence"),
            }
            if preferred
            else None
        ),
        "alternative_hypotheses": [
            {
                "hypothesis_id": h.get("hypothesis_id"),
                "hypothesis": h.get("hypothesis"),
                "status": h.get("status"),
                "evaluation_score": h.get("evaluation_score"),
                "confidence": h.get("confidence"),
            }
            for h in (assigned["alternative_hypotheses"] or [])
        ],
        "support_score": (preferred or (ordered[0] if ordered else {})).get("support_score"),
        "conflict_score": (preferred or (ordered[0] if ordered else {})).get("conflict_score"),
        "coverage_score": (preferred or (ordered[0] if ordered else {})).get("coverage_score"),
        "historical_score": (preferred or (ordered[0] if ordered else {})).get("historical_score"),
        "framework_score": (preferred or (ordered[0] if ordered else {})).get("framework_score"),
        "missing_evidence": (preferred or {}).get("missing_evidence")
        if preferred
        else (ordered[0].get("missing_evidence") if ordered else []),
        "confidence": (preferred or {}).get("confidence")
        if preferred
        else (
            _round(sum(float(h.get("confidence") or 0) for h in ordered) / len(ordered)) if ordered else 0.0
        ),
        "evaluation_reason": (preferred or {}).get("evaluation_reason")
        if preferred
        else (
            "Multiple explanations remain viable; no forced single winner."
            if assigned["outcome"] in {"indeterminate", "plausible_set"}
            else "No preferred hypothesis."
        ),
        "evaluation_version": EVALUATION_VERSION,
        "citations": (preferred or (ordered[0] if ordered else {})).get("citations") or [],
        "outcome": assigned["outcome"],
        "plural": assigned["plural"],
        "forced_single_winner": False,
    }

    avg_support = _round(sum(float(h.get("support_score") or 0) for h in ordered) / len(ordered)) if ordered else 0.0
    avg_conflict = _round(sum(float(h.get("conflict_raw") or 0) for h in ordered) / len(ordered)) if ordered else 0.0

    return {
        "ihe_version": IHE_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "question": question,
        "as_of": as_of,
        "outcome": assigned["outcome"],
        "plural": assigned["plural"],
        "forced_single_winner": False,
        "n_evaluated": len(ordered),
        "n_preferred": 1 if preferred else 0,
        "n_plausible": sum(1 for h in ordered if h.get("status") == "Plausible"),
        "n_indeterminate": sum(1 for h in ordered if h.get("status") == "Indeterminate"),
        "n_rejected": sum(1 for h in ordered if h.get("status") == "Rejected"),
        "evaluated_hypotheses": ordered,
        "report": report,
        "average_support": avg_support,
        "average_conflict_raw": avg_conflict,
        "average_confidence": report.get("confidence"),
        "missing_evidence_frequency": sum(len(h.get("missing_evidence") or []) for h in ordered),
        "guides_judgment": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "iew_changed": False,
        "ihg_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "metadata": dict(metadata or {}),
    }
