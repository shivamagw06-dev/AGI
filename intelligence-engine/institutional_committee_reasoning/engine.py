"""Deterministic Institutional Committee Reasoning — roles, not votes."""

from __future__ import annotations

import re
from typing import Any

from institutional_committee_reasoning.schema import (
    COMMITTEE_VERSION,
    DOWNSIDE_CUES,
    ICR_VERSION,
    UPSIDE_CUES,
)


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _round(x: float, n: int = 2) -> float:
    return round(float(x), n)


def _tilt(hyp: dict[str, Any]) -> float:
    """
    Upside/downside tilt in [-1, +1].
    +1 = strongest upside language; -1 = strongest downside; 0 = balanced.
    Evidence-backed roles use this after IHE ranking — not optimism-by-default.
    """
    blob = _norm(
        " ".join(
            [
                str(hyp.get("hypothesis") or ""),
                str(hyp.get("template_key") or ""),
                str(hyp.get("category") or ""),
            ]
        )
    )
    up = sum(1 for c in UPSIDE_CUES if c in blob)
    down = sum(1 for c in DOWNSIDE_CUES if c in blob)
    # Conflict burden pulls bearish
    conflict = float(hyp.get("conflict_raw") or 0)
    support = float(hyp.get("support_score") or 0) + 1e-6
    conflict_pull = -min(0.45, conflict / 120.0)
    raw = (up - down) / max(1.0, up + down)
    # Blend lexical tilt with conflict pull
    return max(-1.0, min(1.0, 0.75 * raw + conflict_pull + 0.05 * (support / 22.0 - 0.5)))


def _viable(evaluated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for h in evaluated:
        if not isinstance(h, dict):
            continue
        if h.get("status") in {"Rejected", "InsufficientEvidence"}:
            continue
        if str(h.get("hypothesis") or "").lower().startswith("insufficient"):
            continue
        out.append(h)
    return out


def _assumptions(hyp: dict[str, Any], role: str) -> list[str]:
    fw = hyp.get("framework") or "selected framework"
    base = [
        f"The mechanism '{hyp.get('hypothesis')}' remains operative over the analysis horizon",
        f"Evidence weighting and {fw} remain appropriate for this question",
    ]
    if role == "bull":
        base.append("Upside conditions persist without material adverse catalysts")
    elif role == "bear":
        base.append("Downside pressures are not offset by unobserved positive evidence")
    else:
        base.append("Current balance of support vs conflict is representative of reality")
    if hyp.get("missing_evidence"):
        base.append("Missing evidence, if obtained, would not reverse the case ranking")
    return base


def _catalysts(hyp: dict[str, Any], role: str) -> list[str]:
    cats = []
    title = str(hyp.get("hypothesis") or "")
    if role == "bull":
        cats.append(f"Confirmation of: {title}")
        cats.append("Primary filing or management disclosure reinforcing upside mechanism")
    elif role == "bear":
        cats.append(f"Confirmation of downside path: {title}")
        cats.append("Adverse print / guidance / asset-quality signal validating risks")
    else:
        cats.append("Evidence continues to corroborate the base mechanism without regime shift")
    if hyp.get("historical_score") and float(hyp.get("historical_score") or 0) >= 6:
        cats.append("Historical analogue path continues to rhyme with the current setup")
    return cats[:4]


def _risks(hyp: dict[str, Any], role: str) -> list[str]:
    risks = []
    for m in (hyp.get("missing_evidence") or [])[:3]:
        if isinstance(m, dict):
            risks.append(f"Missing: {m.get('item')}")
        else:
            risks.append(f"Missing: {m}")
    if float(hyp.get("conflict_raw") or 0) > 0:
        risks.append("Contradictory evidence already on file may strengthen")
    if role == "bull":
        risks.append("Upside case fails if conflicting evidence becomes dominant")
    elif role == "bear":
        risks.append("Bear case fails if support for the downside mechanism fades")
    else:
        risks.append("Base case fails if a competing hypothesis gains clear evaluation lead")
    return risks[:6]


def _invalidation(hyp: dict[str, Any], role: str) -> list[str]:
    inv = [
        "New primary evidence that falsifies the core mechanism",
        "Evaluation lead reverses to a mutually exclusive competing hypothesis",
    ]
    if role == "bull":
        inv.append("Material rise in conflict_score without matching support")
    elif role == "bear":
        inv.append("Credible upside evidence that outweighs current downside support")
    else:
        inv.append("Committee probabilities reallocate such that base is no longer modal")
    return inv


def _required_conditions(hyp: dict[str, Any], role: str) -> list[str]:
    cond = [
        "Point-in-time evidence remains replay-safe under Temporal Integrity",
        f"Hypothesis '{hyp.get('hypothesis')}' stays eligible under IHE",
    ]
    if role != "base":
        cond.append(f"{role.title()} role remains the strongest {role} interpretation among viable cases")
    return cond


def _analogues(institutional_memory: dict[str, Any] | None, hyp: dict[str, Any]) -> list[str]:
    im = institutional_memory or {}
    out: list[str] = []
    if im.get("have_we_seen_this_before"):
        for mid in (im.get("top_memory_ids") or [])[:3]:
            out.append(str(mid))
        for b in (im.get("surface_bullets") or [])[:2]:
            out.append(str(b)[:160])
    if float(hyp.get("historical_score") or 0) >= 6 and not out:
        out.append("Historical consistency score elevated on evaluated hypothesis")
    return out[:5]


def _framework_alignment(hyp: dict[str, Any], framework_ids: list[str]) -> dict[str, Any]:
    hyp_fw = str(hyp.get("framework") or "")
    aligned = False
    if not framework_ids:
        aligned = True
    elif hyp_fw:
        blob = " ".join(framework_ids).upper()
        aligned = hyp_fw.upper() in blob or any(
            hyp_fw.upper() in f.upper() or f.upper() in hyp_fw.upper() for f in framework_ids
        )
    return {
        "hypothesis_framework": hyp_fw or None,
        "selected_frameworks": list(framework_ids),
        "aligned": aligned,
        "score": float(hyp.get("framework_score") or 0),
    }


def _build_case(
    *,
    role: str,
    hyp: dict[str, Any],
    probability: float,
    institutional_memory: dict[str, Any] | None,
    framework_ids: list[str],
) -> dict[str, Any]:
    cov = float(hyp.get("coverage_score") or 0)
    # Map IHE coverage cap (~16) to 0..1 style coverage for the case
    evidence_coverage = _round(min(1.0, cov / 16.0), 3)
    conf = float(hyp.get("confidence") or 0)
    return {
        "case_name": f"{role.title()} — {hyp.get('hypothesis')}",
        "case_type": role,
        "role_definition": {
            "bull": "Strongest evidence-supported upside interpretation",
            "base": "Interpretation best supported by the current balance of evidence",
            "bear": "Strongest evidence-supported downside interpretation",
        }.get(role),
        "hypothesis_id": hyp.get("hypothesis_id"),
        "hypothesis": hyp.get("hypothesis"),
        "ihe_status": hyp.get("status"),
        "evaluation_score": hyp.get("evaluation_score"),
        "supporting_evidence": list(hyp.get("supporting_evidence") or []),
        "contradictory_evidence": list(hyp.get("contradicting_evidence") or []),
        "underlying_assumptions": _assumptions(hyp, role),
        "required_conditions": _required_conditions(hyp, role),
        "key_catalysts": _catalysts(hyp, role),
        "key_risks": _risks(hyp, role),
        "invalidation_conditions": _invalidation(hyp, role),
        "confidence": _round(conf, 3),
        "probability": _round(probability, 4),
        "probability_pct": _round(100.0 * probability, 2),
        "evidence_coverage": evidence_coverage,
        "historical_analogues": _analogues(institutional_memory, hyp),
        "framework_alignment": _framework_alignment(hyp, framework_ids),
        "missing_evidence": list(hyp.get("missing_evidence") or []),
        "support_score": hyp.get("support_score"),
        "conflict_score": hyp.get("conflict_score"),
        "conflict_raw": hyp.get("conflict_raw"),
        "tilt": _round(_tilt(hyp), 3),
        "citations": list(hyp.get("citations") or [])[:8],
        "evaluation_reason": hyp.get("evaluation_reason"),
        "fabricated": False,
        "llm_used": False,
        "deterministic": True,
    }


def _assign_roles(viable: list[dict[str, Any]]) -> dict[str, dict[str, Any] | None]:
    """
    Roles within the committee (not fixed templates):
      base = best-supported balance (Preferred or top evaluation_score)
      bull = strongest upside interpretation still evidence-backed
      bear = strongest downside interpretation still evidence-backed
    """
    if not viable:
        return {"bull": None, "base": None, "bear": None}

    ordered = sorted(
        viable,
        key=lambda h: (
            -float(h.get("evaluation_score") or 0),
            -float(h.get("support_score") or 0),
            str(h.get("hypothesis_id") or ""),
        ),
    )
    preferred = next((h for h in ordered if h.get("status") == "Preferred"), None)
    base = preferred or ordered[0]

    scored = []
    for h in ordered:
        scored.append((h, _tilt(h), float(h.get("evaluation_score") or 0)))

    bull = None
    bear = None
    # Upside candidates: positive tilt, not identical to base if alternatives exist
    upside = sorted(
        [x for x in scored if x[1] > 0.05],
        key=lambda t: (-t[1], -t[2], str(t[0].get("hypothesis_id"))),
    )
    downside = sorted(
        [x for x in scored if x[1] < -0.05],
        key=lambda t: (t[1], -t[2], str(t[0].get("hypothesis_id"))),  # most negative first
    )

    if upside:
        bull = upside[0][0]
        if bull.get("hypothesis_id") == base.get("hypothesis_id") and len(upside) > 1:
            bull = upside[1][0]
        elif bull.get("hypothesis_id") == base.get("hypothesis_id"):
            # Base itself is the upside case — only emit bull if a distinct alt exists
            bull = None
    if downside:
        bear = downside[0][0]
        if bear.get("hypothesis_id") == base.get("hypothesis_id") and len(downside) > 1:
            bear = downside[1][0]
        elif bear.get("hypothesis_id") == base.get("hypothesis_id"):
            bear = None

    # If we have 2+ viable but no lexical bull/bear, use rank #2 as the opposing role by relative tilt
    if len(ordered) >= 2:
        alt = next(h for h in ordered if h.get("hypothesis_id") != base.get("hypothesis_id"))
        alt_tilt = _tilt(alt)
        if bull is None and bear is None:
            if alt_tilt >= 0:
                bull = alt
            else:
                bear = alt
        elif bull is None and alt_tilt > _tilt(base):
            bull = alt
        elif bear is None and alt_tilt < _tilt(base):
            bear = alt

    # Deduplicate: same hypothesis cannot fill two roles
    ids = {}
    for role, h in (("base", base), ("bull", bull), ("bear", bear)):
        if h is None:
            continue
        hid = h.get("hypothesis_id")
        if hid in ids.values():
            # keep first assigned role
            if role != "base":
                if role == "bull":
                    bull = None
                else:
                    bear = None
        else:
            ids[role] = hid

    return {"bull": bull, "base": base, "bear": bear}


def _probabilities(roles: dict[str, dict[str, Any] | None]) -> dict[str, float]:
    """Relative support given current evidence — always sums to 1.0 across present cases."""
    weights: dict[str, float] = {}
    for role, h in roles.items():
        if h is None:
            continue
        # evaluation_score with mild confidence blend
        w = max(0.01, float(h.get("evaluation_score") or 0) * (0.5 + 0.5 * float(h.get("confidence") or 0.5)))
        weights[role] = w
    if not weights:
        return {}
    total = sum(weights.values()) or 1.0
    raw = {k: v / total for k, v in weights.items()}
    # Fix rounding to exact 1.0
    keys = sorted(raw.keys())
    rounded = {k: _round(raw[k], 4) for k in keys}
    drift = _round(1.0 - sum(rounded.values()), 4)
    if keys:
        rounded[keys[0]] = _round(rounded[keys[0]] + drift, 4)
    return rounded


def deliberate(
    *,
    question: str,
    hypothesis_evaluation: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    framework_ids: list[str] | None = None,
    evidence_weighting: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct Bull/Base/Bear committee cases from evaluated hypotheses."""
    ihe = hypothesis_evaluation or {}
    evaluated = [h for h in (ihe.get("evaluated_hypotheses") or []) if isinstance(h, dict)]
    viable = _viable(evaluated)
    fids = list(framework_ids or (framework_selection or {}).get("framework_ids") or [])

    if ihe.get("outcome") == "insufficient_evidence" or not viable:
        report = {
            "bull_case": None,
            "base_case": None,
            "bear_case": None,
            "committee_summary": (
                "Insufficient evidence for committee deliberation. "
                "No Bull/Base/Bear cases fabricated."
            ),
            "preferred_case": None,
            "alternative_cases": [],
            "probability_distribution": {},
            "confidence": 0.0,
            "major_uncertainties": ["Insufficient evidence-backed hypotheses after IHE"],
            "key_disagreements": [],
            "missing_evidence": [{"item": "Evidence sufficient to support at least one viable hypothesis", "severity": "high"}],
            "committee_version": COMMITTEE_VERSION,
            "citations": [],
            "outcome": "insufficient_evidence",
            "forced_consensus": False,
        }
        return {
            "icr_version": ICR_VERSION,
            "committee_version": COMMITTEE_VERSION,
            "question": question,
            "as_of": as_of,
            "cases": {},
            "report": report,
            "n_cases": 0,
            "probability_sum": 0.0,
            "guides_committee": True,
            "reasoning_changed": False,
            "framework_changed": False,
            "ihe_changed": False,
            "llm_used": False,
            "fabricated": False,
            "deterministic": True,
            "voting_engine": False,
            "metadata": dict(metadata or {}),
        }

    roles = _assign_roles(viable)
    probs = _probabilities(roles)

    cases: dict[str, Any] = {}
    for role in ("bull", "base", "bear"):
        h = roles.get(role)
        if h is None:
            cases[role] = None
            continue
        cases[role] = _build_case(
            role=role,
            hyp=h,
            probability=float(probs.get(role) or 0),
            institutional_memory=institutional_memory,
            framework_ids=fids,
        )

    present = [r for r in ("bull", "base", "bear") if cases.get(r)]
    preferred_role = "base" if cases.get("base") else present[0]
    # Modal probability case is preferred for committee summary
    if probs:
        preferred_role = max(probs.items(), key=lambda kv: (kv[1], 0 if kv[0] != "base" else 0.001))[0]

    # Disagreements: distinct mechanisms across roles
    mechs = []
    for r in present:
        mechs.append((r, str(cases[r].get("hypothesis") or "")))
    disagreements = []
    if len(mechs) >= 2:
        for i in range(len(mechs)):
            for j in range(i + 1, len(mechs)):
                if mechs[i][1] != mechs[j][1]:
                    disagreements.append(
                        {
                            "a": mechs[i][0],
                            "b": mechs[j][0],
                            "a_hypothesis": mechs[i][1],
                            "b_hypothesis": mechs[j][1],
                            "note": "Competing institutional interpretations remain evidence-backed",
                        }
                    )

    missing: list[Any] = []
    for r in present:
        for m in cases[r].get("missing_evidence") or []:
            missing.append(m)
    # Dedup
    seen = set()
    missing_u = []
    for m in missing:
        key = _norm(m.get("item") if isinstance(m, dict) else m)
        if key in seen:
            continue
        seen.add(key)
        missing_u.append(m)

    uncertainties = []
    if disagreements:
        uncertainties.append("Committee retains unresolved competing cases")
    if missing_u:
        uncertainties.append("Critical missing evidence caps confidence")
    if ihe.get("outcome") in {"indeterminate", "plausible_set"}:
        uncertainties.append("IHE outcome was non-unique; committee preserves pluralism")

    confs = [float(cases[r].get("confidence") or 0) for r in present]
    committee_conf = _round(sum(confs) / len(confs), 3) if confs else 0.0
    if missing_u:
        committee_conf = min(committee_conf, 0.55)

    why_preferred = (
        f"Preferred case '{preferred_role}' carries probability "
        f"{_round(100 * float(probs.get(preferred_role) or 0), 2)}% "
        f"as relative support under current evidence (not a forecast)."
    )
    why_alts = (
        "Alternatives remain plausible because contradictory evidence was retained "
        "and no forced consensus was manufactured."
        if len(present) > 1
        else "Only one evidence-backed committee case could be constructed."
    )

    dist = {r: _round(100.0 * float(probs.get(r) or 0), 2) for r in present}
    # Ensure pct sum 100
    if dist:
        drift = _round(100.0 - sum(dist.values()), 2)
        first = sorted(dist.keys())[0]
        dist[first] = _round(dist[first] + drift, 2)

    citations = []
    for r in present:
        citations.extend(cases[r].get("citations") or [])

    report = {
        "bull_case": cases.get("bull"),
        "base_case": cases.get("base"),
        "bear_case": cases.get("bear"),
        "committee_summary": (
            f"Committee constructed {len(present)} evidence-backed case(s) "
            f"({', '.join(present)}). {why_preferred} {why_alts}"
        ),
        "preferred_case": preferred_role,
        "why_preferred": why_preferred,
        "why_alternatives_remain": why_alts,
        "alternative_cases": [r for r in present if r != preferred_role],
        "probability_distribution": dist,
        "confidence": committee_conf,
        "major_uncertainties": uncertainties,
        "key_disagreements": disagreements,
        "missing_evidence": missing_u[:12],
        "committee_version": COMMITTEE_VERSION,
        "citations": citations[:20],
        "outcome": "deliberated",
        "n_cases": len(present),
        "forced_consensus": False,
        "voting_engine": False,
    }

    return {
        "icr_version": ICR_VERSION,
        "committee_version": COMMITTEE_VERSION,
        "question": question,
        "as_of": as_of,
        "cases": cases,
        "report": report,
        "n_cases": len(present),
        "probability_sum": _round(sum(float(probs.get(r) or 0) for r in present), 4),
        "probability_distribution": dist,
        "preferred_case": preferred_role,
        "guides_committee": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "ihe_changed": False,
        "ihg_changed": False,
        "iew_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "voting_engine": False,
        "metadata": dict(metadata or {}),
    }
