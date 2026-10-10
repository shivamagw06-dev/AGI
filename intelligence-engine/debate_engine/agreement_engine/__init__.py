"""Agreement engine — shared conclusions, evidence, assumptions and risks."""

from __future__ import annotations

from typing import Any


def find_agreement(
    positions: list[dict[str, Any]],
    thesis: dict[str, Any],
) -> dict[str, Any]:
    supporting = [
        p for p in positions if p.get("position") in ("Strong Support", "Support")
    ]
    common = [
        {
            "analyst": p["analyst"],
            "conclusion": p["conclusion"],
            "confidence": p["confidence"],
        }
        for p in supporting
    ]
    shared_assumptions: dict[str, list[str]] = {}
    for p in positions:
        for assumption in p.get("assumptions") or []:
            key = (
                "No structural break"
                if "structural break" in assumption
                else assumption
            )
            shared_assumptions.setdefault(key, []).append(p["analyst"])

    shared = [
        {"assumption": text, "analysts": analysts}
        for text, analysts in shared_assumptions.items()
        if len(analysts) >= 2
    ]
    support_evidence = (
        (thesis.get("contradictions") or {}).get("strongest_supporting_evidence")
        or []
    )
    risks = [
        {
            "risk": r.get("risk"),
            "analysts": ["Risk", "Portfolio"],
            "probability": r.get("probability"),
        }
        for r in (thesis.get("risks") or [])[:4]
    ]
    return {
        "common_conclusions": common,
        "agreement_count": len(common),
        "shared_evidence": support_evidence[:5],
        "shared_assumptions": shared,
        "shared_risks": risks,
        "supporting_analysts": [p["analyst"] for p in supporting],
    }
