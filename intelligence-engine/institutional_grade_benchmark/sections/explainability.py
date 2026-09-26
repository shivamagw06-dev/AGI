"""Section F — Explainability / lineage (100 pts). Broken lineage = fail."""

from __future__ import annotations

from typing import Any

from institutional_grade_benchmark.schema import LINEAGE_CHAIN
from institutional_grade_benchmark.sections._common import section_result
from institutional_grade_benchmark.store import manual_section_scores


def score_explainability(*, mode: str = "harness") -> dict[str, Any]:
    manual = manual_section_scores().get("explainability")
    if manual:
        return section_result(
            code="F",
            key="explainability",
            title="Explainability",
            score=float(manual["score"]),
            max_score=100,
            detail="Recorded manual section score",
        )

    items = []
    broken = False
    per = 100.0 / len(LINEAGE_CHAIN)
    total = 0.0
    for hop in LINEAGE_CHAIN:
        present = True
        if mode != "harness":
            present = _probe_lineage_hop(hop)
        if not present:
            broken = True
        pts = per if present else 0.0
        total += pts
        items.append({"hop": hop, "ok": present, "score": round(pts, 3)})

    if broken:
        total = 0.0  # Broken lineage = fail

    return section_result(
        code="F",
        key="explainability",
        title="Explainability",
        score=total,
        max_score=100,
        detail="Decision→Risk→Observation→Evidence→Raw source",
        items=items,
        harness_estimate=(mode == "harness"),
        meta={"broken_lineage": broken, "chain": list(LINEAGE_CHAIN)},
    )


def _probe_lineage_hop(hop: str) -> bool:
    mapping = {
        "decision": "institutional_decision.production",
        "risk": "institutional_portfolio_risk.production",
        "observation": "institutional_observation.production",
        "evidence": "institutional_graph.production",
        "raw_source": "institutional_architecture.production",
    }
    mod = mapping.get(hop)
    if not mod:
        return False
    try:
        m = __import__(mod, fromlist=["health"])
        out = m.health()
        return isinstance(out, dict)
    except Exception:  # noqa: BLE001
        return False
