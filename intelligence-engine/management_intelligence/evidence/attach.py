"""Evidence pack for management intelligence — no opinion without source hook."""

from __future__ import annotations

from typing import Any


def evidence_pack(profile: dict[str, Any], *, confidence: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for g in profile.get("guidance_events") or []:
        rows.append(
            {
                "type": "guidance",
                "ref": g.get("event_id"),
                "source_doc": g.get("source_doc"),
                "as_of": g.get("as_of"),
                "evidence_tier": g.get("evidence_tier"),
                "statement": g.get("statement"),
            }
        )
    for c in profile.get("credibility_claims") or []:
        rows.append(
            {
                "type": "credibility_claim",
                "ref": c.get("claim_id"),
                "source_doc": c.get("source_doc"),
                "as_of": c.get("as_of"),
                "statement": c.get("statement"),
                "outcome": c.get("outcome"),
            }
        )
    for d in profile.get("capital_allocation") or []:
        rows.append(
            {
                "type": "capital_decision",
                "ref": d.get("decision_id"),
                "source_doc": d.get("source_doc"),
                "as_of": d.get("as_of"),
                "decision": d.get("decision"),
                "value_label": d.get("value_label"),
            }
        )
    coverage = min(100.0, 20.0 + 8.0 * len(rows))
    return {
        "rows": rows,
        "count": len(rows),
        "evidence_coverage": coverage,
        "confidence_explain": confidence.get("explain"),
        "rule": "No subjective management opinion without evidence hook",
    }
