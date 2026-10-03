"""Evidence conflict mapping for each disagreement."""

from __future__ import annotations

from typing import Any


def _texts(items: list[Any]) -> list[str]:
    out = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("text") or item.get("statement")
        else:
            text = str(item)
        if text:
            out.append(str(text))
    return out


def map_evidence_conflicts(
    disagreements: dict[str, Any],
    positions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_analyst = {p["analyst"]: p for p in positions}
    conflicts = []
    for i, d in enumerate(disagreements.get("conflicts") or [], start=1):
        left = by_analyst[d["analyst_a"]]
        right = by_analyst[d["analyst_b"]]
        support = _texts(left.get("supporting_evidence") or [])
        opposing = _texts(
            right.get("contradicting_evidence")
            or right.get("supporting_evidence")
            or []
        )
        required = list(
            dict.fromkeys(
                (left.get("required_evidence") or [])
                + (right.get("required_evidence") or [])
            )
        )
        quality = round(
            100
            * (
                0.4 * float(left.get("confidence") or 0.5)
                + 0.4 * float(right.get("confidence") or 0.5)
                + 0.2 * (1.0 if support and opposing else 0.4)
            )
        )
        conflicts.append(
            {
                "id": f"EC-{i:03d}",
                "disagreement_id": d["id"],
                "topic": d["topic"],
                "supporting_evidence": support[:4]
                or [f"{left['analyst']} position requires direct verification"],
                "opposing_evidence": opposing[:4]
                or [f"{right['analyst']} position requires direct verification"],
                "evidence_quality": quality,
                "evidence_gaps": required[:4],
                "required_additional_evidence": required[:4]
                or [f"Independent evidence resolving {d['topic']}"],
                "resolvable": True,
            }
        )
    return conflicts
