"""Deterministic hypothesis generation + IEW-weighted scoring."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from institutional_hypothesis_generation.catalog import active_catalog_id, load_catalog
from institutional_hypothesis_generation.schema import (
    CLEAR_LEADER_GAP,
    HYPOTHESIS_VERSION,
    IHG_VERSION,
    MAX_HYPOTHESES,
    MIN_HYPOTHESES,
    REJECT_OVERALL_BELOW,
    WEAK_SUPPORT_BELOW,
)


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _evidence_blob(ev: dict[str, Any]) -> str:
    parts = [
        ev.get("title"),
        ev.get("reason"),
        ev.get("source"),
        ev.get("evidence_id"),
        " ".join(str(c) for c in (ev.get("citations") or [])[:3]),
    ]
    classes = ev.get("classes") or {}
    if isinstance(classes, dict):
        parts.extend(str(v) for v in classes.values())
    return _norm(" ".join(str(p) for p in parts if p))


def _cue_hit(blob: str, cues: tuple[str, ...] | list[str]) -> bool:
    return any(c and c in blob for c in cues)


def _stable_id(family_id: str, key: str, question: str) -> str:
    digest = hashlib.sha1(f"{family_id}|{key}|{_norm(question)[:120]}".encode("utf-8")).hexdigest()[:10]
    return f"HYP-{family_id}-{key}-{digest}"


def select_families(question: str, catalog: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Pick matching families; prefer specific over generic_why when both match."""
    cat = catalog or load_catalog()
    q = _norm(question)
    matched: list[dict[str, Any]] = []
    for fam in cat.get("families") or []:
        cues = tuple(fam.get("cues") or ())
        if any(c in q for c in cues):
            matched.append(fam)
    if not matched:
        # Fall back to generic_why if present
        for fam in cat.get("families") or []:
            if fam.get("family_id") == "generic_why":
                return [fam]
        return []
    # Drop generic when a more specific family matched
    specific = [f for f in matched if f.get("family_id") != "generic_why"]
    return specific or matched


def _match_evidence(
    template: dict[str, Any],
    weighted: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    support: list[dict[str, Any]] = []
    conflict: list[dict[str, Any]] = []
    support_cues = tuple(template.get("support_cues") or ())
    conflict_cues = tuple(template.get("conflict_cues") or ())
    for ev in weighted:
        if ev.get("eligible") is False:
            continue
        blob = _evidence_blob(ev)
        if _cue_hit(blob, support_cues):
            support.append(ev)
        if _cue_hit(blob, conflict_cues):
            conflict.append(ev)
    return support, conflict


def _score_hypothesis(
    *,
    family: dict[str, Any],
    template: dict[str, Any],
    question: str,
    support: list[dict[str, Any]],
    conflict: list[dict[str, Any]],
    framework_hint: str | None,
) -> dict[str, Any]:
    support_score = round(sum(float(e.get("weight_score") or 0.0) for e in support), 2)
    conflict_score = round(sum(float(e.get("weight_score") or 0.0) for e in conflict), 2)
    # Net with soft conflict penalty — never ignore conflict
    overall = round(max(0.0, support_score - 0.65 * conflict_score), 2)
    conf = 0.0
    if support_score > 0:
        conf = support_score / (support_score + conflict_score + 1e-6)
        # dampen when thin support
        if support_score < WEAK_SUPPORT_BELOW:
            conf *= 0.55
        conf = round(min(0.95, max(0.05, conf)), 3)

    framework = framework_hint or template.get("framework")
    citations: list[dict[str, Any]] = []
    for e in support[:5] + conflict[:3]:
        citations.append(
            {
                "evidence_id": e.get("evidence_id"),
                "source": e.get("source"),
                "weight_score": e.get("weight_score"),
                "title": e.get("title"),
                "role": "support" if e in support else "conflict",
            }
        )

    why_created = (
        f"Family '{family.get('family_id')}' matched the question; "
        f"template '{template.get('key')}' is an institutional explanation class."
    )
    why_scored = (
        f"Weighted support {support_score:g} from {len(support)} evidence item(s); "
        f"weighted conflict {conflict_score:g} from {len(conflict)} item(s); "
        f"overall = support − 0.65×conflict = {overall:g}."
    )

    status = "Active"
    reject_reason = None
    if support_score < WEAK_SUPPORT_BELOW or overall < REJECT_OVERALL_BELOW:
        status = "Rejected"
        reject_reason = (
            f"Weak evidence backing (support={support_score:g}, overall={overall:g}); "
            "kept visible for reasoning inspection."
        )

    reason = " | ".join(
        [
            f"Why created: {why_created}",
            f"Why scored: {why_scored}",
            f"Why {'rejected' if status == 'Rejected' else 'retained'}: "
            + (reject_reason or "Meets minimum evidence-backed support threshold."),
        ]
    )

    return {
        "hypothesis_id": _stable_id(str(family.get("family_id")), str(template.get("key")), question),
        "hypothesis": template.get("hypothesis"),
        "category": template.get("category"),
        "framework": framework,
        "family_id": family.get("family_id"),
        "template_key": template.get("key"),
        "supporting_evidence": [e.get("evidence_id") for e in support],
        "contradicting_evidence": [e.get("evidence_id") for e in conflict],
        "weighted_support": support_score,
        "weighted_conflict": conflict_score,
        "support_score": support_score,
        "conflict_score": conflict_score,
        "overall_score": overall,
        "confidence": conf,
        "status": status,
        "priority": None,
        "share": None,
        "reason": reason,
        "citations": citations,
        "reject_reason": reject_reason,
        "hypothesis_version": HYPOTHESIS_VERSION,
        "ihg_version": IHG_VERSION,
        "fabricated": False,
        "llm_used": False,
        "deterministic": True,
    }


def _assign_plural_outcomes(hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Normalize Active/Rejected scores into shares. Do NOT force a single winner.
    Preferred only when a clear share gap exists; otherwise Contested.
    """
    if not hypotheses:
        return {
            "outcome": "insufficient_evidence",
            "winning_hypothesis_ids": [],
            "plural": True,
            "forced_single_winner": False,
        }

    # Ranking key: overall then support then id
    ordered = sorted(
        hypotheses,
        key=lambda h: (
            -float(h.get("overall_score") or 0.0),
            -float(h.get("support_score") or 0.0),
            str(h.get("hypothesis_id") or ""),
        ),
    )
    for i, h in enumerate(ordered, start=1):
        h["priority"] = i

    active = [h for h in ordered if h.get("status") != "Rejected"]
    pool = active if active else ordered  # if all rejected, still show shares among them
    total = sum(max(0.0, float(h.get("overall_score") or 0.0)) for h in pool) or 1.0
    for h in ordered:
        if h in pool:
            h["share"] = round(max(0.0, float(h.get("overall_score") or 0.0)) / total, 4)
        else:
            h["share"] = 0.0

    # Contested vs Preferred among non-rejected
    winners: list[str] = []
    if active:
        top = active[0]
        second_share = float(active[1]["share"]) if len(active) > 1 else 0.0
        top_share = float(top.get("share") or 0.0)
        if len(active) == 1 or (top_share - second_share) >= CLEAR_LEADER_GAP:
            top["status"] = "Preferred"
            # annotate preference reason
            top["reason"] = (top.get("reason") or "") + (
                f" | Why preferred: clear lead (share={top_share:.1%} vs next {second_share:.1%})."
            )
            winners = [str(top.get("hypothesis_id"))]
            outcome = "preferred"
            plural = len(active) > 1
        else:
            # Mark close leaders Contested
            contested_ids: list[str] = []
            for h in active:
                if abs(float(h.get("share") or 0.0) - top_share) <= CLEAR_LEADER_GAP:
                    h["status"] = "Contested"
                    h["reason"] = (h.get("reason") or "") + (
                        " | Why not sole winner: evidence supports multiple plausible explanations; "
                        "no forced single hypothesis."
                    )
                    contested_ids.append(str(h.get("hypothesis_id")))
            winners = contested_ids
            outcome = "contested"
            plural = True
    else:
        outcome = "all_rejected"
        plural = True
        winners = []

    return {
        "outcome": outcome,
        "winning_hypothesis_ids": winners,
        "plural": plural,
        "forced_single_winner": False,
        "hypotheses": ordered,
    }


def generate_hypotheses(
    *,
    question: str,
    weighted_evidence: list[dict[str, Any]] | None = None,
    framework_ids: list[str] | None = None,
    intent: str | None = None,
    playbook_id: str | None = None,
    weight_version: str | None = None,
    catalog_id: str | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Produce 2–5 evidence-backed hypotheses or an Insufficient Evidence result.
    Never fabricates. Never forces a single winner.
    """
    catalog = load_catalog(catalog_id)
    weighted = [w for w in (weighted_evidence or []) if isinstance(w, dict)]
    eligible = [w for w in weighted if w.get("eligible") is not False]

    families = select_families(question, catalog)
    framework_hint = (framework_ids or [None])[0]

    candidates: list[dict[str, Any]] = []
    for fam in families:
        for tmpl in fam.get("hypotheses") or []:
            support, conflict = _match_evidence(tmpl, eligible)
            if not support:
                # Never invent — skip templates without supporting evidence
                continue
            hyp = _score_hypothesis(
                family=fam,
                template=tmpl,
                question=question,
                support=support,
                conflict=conflict,
                framework_hint=str(framework_hint) if framework_hint else None,
            )
            candidates.append(hyp)

    # Deduplicate by template_key across families (keep highest overall)
    by_key: dict[str, dict[str, Any]] = {}
    for h in candidates:
        k = str(h.get("template_key") or h.get("hypothesis_id"))
        prev = by_key.get(k)
        if prev is None or float(h.get("overall_score") or 0) > float(prev.get("overall_score") or 0):
            by_key[k] = h
    candidates = list(by_key.values())

    # Cap to MAX, keep best by overall (but keep rejected among top set for visibility)
    candidates = sorted(
        candidates,
        key=lambda h: (-float(h.get("overall_score") or 0.0), str(h.get("hypothesis_id") or "")),
    )[:MAX_HYPOTHESES]

    insufficient = False
    insufficient_reason = None
    if len(eligible) == 0:
        insufficient = True
        insufficient_reason = "No eligible weighted evidence available after IEW/TIRC."
    elif len(candidates) < MIN_HYPOTHESES:
        insufficient = True
        insufficient_reason = (
            f"Only {len(candidates)} evidence-backed hypothesis template(s) matched; "
            f"need at least {MIN_HYPOTHESES}. Refusing to fabricate."
        )

    if insufficient:
        placeholder = {
            "hypothesis_id": _stable_id("insufficient", "none", question),
            "hypothesis": "Insufficient Evidence",
            "category": "Mixed",
            "framework": framework_hint,
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "weighted_support": 0.0,
            "weighted_conflict": 0.0,
            "support_score": 0.0,
            "conflict_score": 0.0,
            "overall_score": 0.0,
            "confidence": 0.0,
            "status": "InsufficientEvidence",
            "priority": 1,
            "share": 1.0,
            "reason": f"Why created: gate. Why scored: n/a. Why preferred: none — {insufficient_reason}",
            "citations": [],
            "hypothesis_version": active_catalog_id(),
            "ihg_version": IHG_VERSION,
            "fabricated": False,
            "llm_used": False,
            "deterministic": True,
        }
        return {
            "ihg_version": IHG_VERSION,
            "hypothesis_version": active_catalog_id(),
            "weight_version": weight_version,
            "question": question,
            "intent": intent,
            "playbook": playbook_id,
            "as_of": as_of,
            "families": [f.get("family_id") for f in families],
            "n_hypotheses": 1,
            "hypotheses": [placeholder],
            "outcome": "insufficient_evidence",
            "winning_hypothesis_ids": [],
            "plural": False,
            "forced_single_winner": False,
            "insufficient_evidence": True,
            "insufficient_reason": insufficient_reason,
            "guides_hypothesis_space": True,
            "reasoning_changed": False,
            "llm_used": False,
            "fabricated": False,
            "deterministic": True,
            "metadata": dict(metadata or {}),
        }

    pluralized = _assign_plural_outcomes(candidates)
    ordered = pluralized["hypotheses"]

    return {
        "ihg_version": IHG_VERSION,
        "hypothesis_version": active_catalog_id(),
        "weight_version": weight_version,
        "question": question,
        "intent": intent,
        "playbook": playbook_id,
        "as_of": as_of,
        "families": [f.get("family_id") for f in families],
        "n_hypotheses": len(ordered),
        "hypotheses": ordered,
        "outcome": pluralized["outcome"],
        "winning_hypothesis_ids": pluralized["winning_hypothesis_ids"],
        "plural": pluralized["plural"],
        "forced_single_winner": False,
        "insufficient_evidence": False,
        "average_confidence": round(
            sum(float(h.get("confidence") or 0) for h in ordered) / max(1, len(ordered)), 3
        ),
        "n_rejected": sum(1 for h in ordered if h.get("status") == "Rejected"),
        "n_contested": sum(1 for h in ordered if h.get("status") == "Contested"),
        "guides_hypothesis_space": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "iew_changed": False,
        "temporal_integrity_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "metadata": dict(metadata or {}),
    }
