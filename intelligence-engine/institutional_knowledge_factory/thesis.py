"""Thesis engine — re-evaluate when assertions change."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_factory.schema import THESIS_COMPONENTS


def evaluate_thesis(
    iko: dict[str, Any],
    changes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Re-evaluate investment thesis based on current claims and recent changes."""
    changes = changes or []
    claims = list(iko.get("claims") or [])
    entity_id = iko.get("entity_id") or "ENTITY"
    company = (iko.get("identity") or {}).get("company_name") or entity_id

    supported = [c for c in claims if str(c.get("state")) == "SUPPORTED"]
    contradicted = [c for c in claims if str(c.get("state")) == "CONTRADICTED"]
    unknowns = [c for c in claims if str(c.get("state")) == "UNKNOWN"]
    under_review = [c for c in claims if str(c.get("state")) == "UNDER_REVIEW"]

    bull_points = [c.get("statement") for c in supported if c.get("claim_type") in {"business", "financial", "growth"}][:3]
    bear_points = [c.get("statement") for c in contradicted + under_review if c.get("claim_type") in {"risk", "monitoring"}][:3]

    thesis_claim = next((c for c in claims if c.get("template_id") == "CLAIM_INVESTMENT_THESIS_CORE"), None)
    current = thesis_claim.get("statement") if thesis_claim else f"Institutional thesis on {company} under formation."

    material_changes = [c for c in changes if c.get("impact") in {"material_upgrade", "material_downgrade", "new"}]

    re_evaluated = bool(material_changes) or bool(contradicted) or bool(under_review)

    return {
        "entity_id": entity_id,
        "re_evaluated": re_evaluated,
        "components": list(THESIS_COMPONENTS),
        "current_thesis": current,
        "bull_thesis": bull_points or [f"{company} franchise quality remains supported by evidence."],
        "bear_thesis": bear_points or [f"Material unknowns remain on {company}."],
        "key_assumptions": [c.get("statement") for c in supported if c.get("required") is not False][:5],
        "unknowns": [c.get("statement") for c in unknowns[:5]],
        "invalidation_conditions": [
            c.get("statement") for c in contradicted + under_review
        ] or [f"Evidence contradicting core business quality claims on {company}."],
        "material_change_count": len(material_changes),
        "thesis_status": (
            "under_review" if contradicted or under_review
            else "supported" if len(supported) >= 3
            else "forming"
        ),
    }
