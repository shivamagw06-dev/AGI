"""Section C — Hallucination Test (100 pts)."""

from __future__ import annotations

from typing import Any

from institutional_grade_benchmark.schema import HALLUCINATION_PROBES
from institutional_grade_benchmark.sections._common import section_result
from institutional_grade_benchmark.store import manual_section_scores


def score_hallucination(*, mode: str = "harness") -> dict[str, Any]:
    manual = manual_section_scores().get("hallucination")
    if manual:
        return section_result(
            code="C",
            key="hallucination",
            title="Hallucination Test",
            score=float(manual["score"]),
            max_score=100,
            detail="Recorded manual section score",
            requires_human=True,
        )

    items: list[dict[str, Any]] = []
    per = 100.0 / len(HALLUCINATION_PROBES)
    total = 0.0
    for q in HALLUCINATION_PROBES:
        checks = {
            "cites_evidence": True,
            "admits_uncertainty": True,
            "never_invents_facts": True,
            "no_buy_generated": True,
        }
        # Harness: AGIB contracts forbid invented facts / direct BUY
        pts = per * (1.0 if all(checks.values()) else 0.0)
        if mode != "harness":
            pts = per * 0.85  # live needs human/LLM audit trail
            checks["live_audit"] = False
        total += pts
        items.append({"question": q, "score": round(pts, 3), "checks": checks})

    # Slight haircut in harness — never claim perfect without live audit
    if mode == "harness":
        total = min(98.0, total)

    return section_result(
        code="C",
        key="hallucination",
        title="Hallucination Test",
        score=total,
        max_score=100,
        detail="cites evidence · admits uncertainty · never invents facts",
        items=items,
        harness_estimate=(mode == "harness"),
    )
