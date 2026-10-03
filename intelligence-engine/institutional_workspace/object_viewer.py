"""RW-01 object viewer — normalize any institutional object for workspace display."""

from __future__ import annotations

from typing import Any, Optional


def view_object(
    object_type: str,
    payload: Optional[dict[str, Any]] = None,
    *,
    object_id: str = "",
) -> dict[str, Any]:
    data = dict(payload or {})
    oid = object_id or str(
        data.get("decision_id")
        or data.get("risk_id")
        or data.get("policy_id")
        or data.get("resolution_id")
        or data.get("id")
        or object_type
    )
    summary_fields = {
        "CompanyDecision": ("recommendation", "confidence", "conviction"),
        "PortfolioRisk": ("overall_risk", "risk_id"),
        "PolicyAssessment": ("overall_status", "compliance_score"),
        "PortfolioDecision": ("recommendation", "investment_posture", "rule_path"),
        "CommitteeResolution": ("status", "outcome"),
        "Observation": ("title", "severity"),
        "Forecast": ("title", "summary"),
        "Evidence": ("title", "source_type"),
    }
    fields = summary_fields.get(object_type, ())
    summary = {k: data.get(k) for k in fields if k in data}
    if object_type == "PortfolioRisk" and "concentration" in data:
        summary["concentration_level"] = (data.get("concentration") or {}).get("level")
    if object_type == "PolicyAssessment" and "violations" in data:
        summary["violation_count"] = len(data.get("violations") or [])

    return {
        "object_type": object_type,
        "object_id": oid,
        "label": str(data.get("title") or data.get("recommendation") or data.get("status") or object_type),
        "summary": summary,
        "payload": data,
        "lineage_position": {
            "CompanyDecision": "Company Decision",
            "PortfolioRisk": "Portfolio Risk",
            "PolicyAssessment": "Policy Assessment",
            "PortfolioDecision": "Portfolio Decision",
            "CommitteeResolution": "Committee Resolution",
            "Evidence": "Evidence",
        }.get(object_type, object_type),
        "mutates_system_intelligence": False,
    }
