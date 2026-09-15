"""Module 8 — Institutional Debate.

Every disagreement explained — never averaged away.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iki.decision_policies import dominant_lens, policy_for
from institutional_reasoning.iki.mental_models import evaluate_authors
from institutional_reasoning.iki.registry import get_framework

DEBATE_VERSION = "institutional-debate-v1.0.0"


def debate(
    *,
    question_type: str,
    entity_id: str | None,
    applicability: dict[str, Any],
    framework_results: list[dict[str, Any]],
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    authors = evaluate_authors(str(entity_id or ""), evidence)
    policy = policy_for(question_type)
    lens = dominant_lens(question_type)

    executed = [r for r in framework_results if r.get("status") == "executed"]
    rejected = [
        s
        for s in (applicability.get("rejected") or [])
    ]
    applicable = applicability.get("applicable") or []

    conflicts: list[dict[str, Any]] = []
    # Author-level conflicts
    a_map = authors.get("authors") or {}
    stances = {k: v.get("stance") for k, v in a_map.items()}
    if stances.get("Graham") == "rejects" and stances.get("Damodaran") in {
        "supports",
        "supports_growth",
        "conditional",
    }:
        conflicts.append(
            {
                "type": "cross_author",
                "left": "Graham",
                "right": "Damodaran",
                "explanation": (
                    "Graham rejects speculative / thin-MoS situations; Damodaran still "
                    "runs growth-relative valuation. Disagreement is philosophical, not a data error."
                ),
                "evidence_shown": True,
            }
        )
    if stances.get("Buffett") == "rejects" and stances.get("Damodaran") in {
        "supports",
        "supports_growth",
        "conditional",
    }:
        conflicts.append(
            {
                "type": "cross_author",
                "left": "Buffett",
                "right": "Damodaran",
                "explanation": (
                    "Buffett wonderful-business screen rejects the franchise; Damodaran "
                    "relative/growth tools may still price it. Committee must explain dominance."
                ),
                "evidence_shown": True,
            }
        )

    # Framework-level conflicts among executed
    for i, a in enumerate(executed):
        for b in executed[i + 1 :]:
            sa = get_framework(a["framework_id"])
            if sa and b["framework_id"] in (sa.competing_frameworks or ()):
                conflicts.append(
                    {
                        "type": "cross_framework",
                        "left": a["framework_id"],
                        "right": b["framework_id"],
                        "explanation": (
                            f"{a.get('name')} competes with {b.get('name')}; both results retained."
                        ),
                        "evidence_shown": True,
                    }
                )

    # Dominance resolution via applicability + policy lens + calibration band
    ranked = sorted(applicable, key=lambda s: -float(s.get("score") or 0))
    dominant = ranked[0] if ranked else None
    resolution = "No applicable framework"
    if dominant:
        fid = dominant["framework_id"]
        spec = get_framework(fid)
        school = (spec.school if spec else "") or "institutional"
        if school == "damodaran" or "rel_val" in fid or "dcf" in fid:
            resolution = "Growth / relative (Damodaran) framework dominates."
        elif school == "graham":
            resolution = "Graham margin-of-safety framework dominates."
        elif school == "buffett":
            resolution = "Buffett quality framework dominates."
        elif fid == "residual_income":
            resolution = "Residual income dominates (financial institution path)."
        else:
            resolution = f"{dominant.get('framework_id')} dominates by applicability score."
        resolution += f" Decision policy lens: {lens}."

    findings = []
    for s in ranked[:5]:
        findings.append(
            f"{s['framework_id']}: applicability {s['score']}% "
            f"({'applicable' if s.get('applicable') else 'rejected'}) — "
            + "; ".join(s.get("reasons") or [])
        )
    for c in conflicts:
        findings.append(f"Conflict {c['left']} vs {c['right']}: {c['explanation']}")

    return {
        "debate_version": DEBATE_VERSION,
        "policy": policy,
        "dominant_lens": lens,
        "authors": a_map,
        "conflicts": conflicts,
        "resolution": resolution,
        "dominant_framework": (dominant or {}).get("framework_id"),
        "findings": findings,
        "executed_ids": [r.get("framework_id") for r in executed],
        "rejected": rejected,
    }
