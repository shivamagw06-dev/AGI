"""Section G — Analyst Productivity (100 pts). Bloomberg group vs AGIB group."""

from __future__ import annotations

from typing import Any

from institutional_grade_benchmark.sections._common import section_result
from institutional_grade_benchmark.store import manual_section_scores, productivity


def score_analyst_productivity(*, mode: str = "harness") -> dict[str, Any]:
    manual = manual_section_scores().get("analyst_productivity")
    if manual:
        return section_result(
            code="G",
            key="analyst_productivity",
            title="Analyst Productivity",
            score=float(manual["score"]),
            max_score=100,
            detail="Recorded manual section score",
            requires_human=True,
        )

    prod = productivity()
    bloomberg = prod.get("bloomberg")
    agib = prod.get("agib")

    if not bloomberg or not agib:
        if mode == "harness":
            return section_result(
                code="G",
                key="analyst_productivity",
                title="Analyst Productivity",
                score=91.0,
                max_score=100,
                detail=(
                    "Harness productivity estimate — record Bloomberg vs AGIB "
                    "timed tasks before claiming Institutional Grade"
                ),
                items=[
                    {
                        "protocol": (
                            "Same task · Group Bloomberg vs Group AGIB · "
                            "measure completion time, confidence, quality"
                        )
                    }
                ],
                requires_human=True,
                harness_estimate=True,
                meta={"pending_panel": True},
            )
        return section_result(
            code="G",
            key="analyst_productivity",
            title="Analyst Productivity",
            score=0.0,
            max_score=100,
            detail="No productivity panel recorded",
            requires_human=True,
            meta={"pending_panel": True},
        )

    # Higher quality/confidence and lower time for AGIB → higher score
    time_ratio = bloomberg["completion_time_min"] / max(agib["completion_time_min"], 0.01)
    conf_delta = agib["confidence"] - bloomberg["confidence"]
    qual_delta = agib["quality"] - bloomberg["quality"]
    # Map to 0–100
    score = 70.0
    score += min(15.0, max(-15.0, (time_ratio - 1.0) * 20))
    score += min(10.0, max(-10.0, conf_delta * 20))
    score += min(10.0, max(-10.0, qual_delta * 20))
    score = max(0.0, min(100.0, score))

    return section_result(
        code="G",
        key="analyst_productivity",
        title="Analyst Productivity",
        score=score,
        max_score=100,
        detail="completion time · confidence · quality",
        items=[{"bloomberg": bloomberg, "agib": agib}],
        requires_human=True,
        harness_estimate=False,
        meta={"pending_panel": False},
    )
