"""P6.8 Publication Pipeline — governance-gated publication-ready formats."""

from __future__ import annotations

from typing import Any

from autonomous_research.schema import PUBLICATION_TYPES
from autonomous_research.util import now_iso, today


def build_publications(
    *,
    morning_brief: dict[str, Any] | None = None,
    drafts: list[dict[str, Any]] | None = None,
    qa_results: dict[str, Any] | None = None,
    themes: dict[str, Any] | None = None,
    portfolio_review: dict[str, Any] | None = None,
    governance_approved_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Only QA-passed drafts may enter the pipeline.
    Publication still requires explicit governance approval flag.
    """
    approved = set(governance_approved_ids or [])
    qa_by = {}
    for r in (qa_results or {}).get("results") or []:
        qa_by[(r.get("entity") or "").upper()] = r.get("qa") or {}

    pipeline = []
    rejected = []

    # Morning / evening briefs from IOL daily brief
    if morning_brief:
        pub = {
            "id": f"morning_brief:{today()}",
            "pub_type": "morning_brief",
            "title": morning_brief.get("title") or "Morning Brief",
            "status": "ready_for_governance",
            "qa_pass": True,
            "governance_approved": f"morning_brief:{today()}" in approved,
            "body": {
                "headline": morning_brief.get("headline"),
                "sections": morning_brief.get("sections"),
            },
            "issues_recommendations": False,
        }
        if pub["governance_approved"]:
            pub["status"] = "published_pending_external"
        pipeline.append(pub)

    for d in drafts or []:
        ent = (d.get("entity") or "").upper()
        qa = qa_by.get(ent) or {}
        pub_id = f"research_note:{ent}:{d.get('research_type')}"
        if not qa.get("qa_pass"):
            rejected.append(
                {
                    "id": pub_id,
                    "company": d.get("company"),
                    "reason": "qa_blocked",
                    "failures": qa.get("failures") or [],
                }
            )
            continue
        gov = pub_id in approved
        pipeline.append(
            {
                "id": pub_id,
                "pub_type": "research_note",
                "title": f"{d.get('company')} — {str(d.get('research_type') or '').replace('_', ' ').title()}",
                "entity": d.get("entity"),
                "status": "published_pending_external" if gov else "ready_for_governance",
                "qa_pass": True,
                "governance_approved": gov,
                "memory_version": d.get("memory_version"),
                "citations_n": len(d.get("citations") or []),
                "draft_ref": {
                    "research_type": d.get("research_type"),
                    "priority": d.get("priority"),
                    "opportunity_score": d.get("opportunity_score"),
                },
                "issues_recommendations": False,
            }
        )

    # Theme / weekly shells (never auto-approved)
    if themes and (themes.get("themes") or []):
        top = (themes.get("themes") or [])[:3]
        pipeline.append(
            {
                "id": f"theme_report:{today()}",
                "pub_type": "theme_report",
                "title": "Theme Strength Snapshot",
                "status": "ready_for_governance",
                "qa_pass": True,
                "governance_approved": f"theme_report:{today()}" in approved,
                "body": {"themes": top},
                "issues_recommendations": False,
            }
        )

    if portfolio_review and portfolio_review.get("holdings"):
        pipeline.append(
            {
                "id": f"weekly_review:portfolio:{today()}",
                "pub_type": "weekly_review",
                "title": "Portfolio Research Review",
                "status": "ready_for_governance",
                "qa_pass": True,
                "governance_approved": f"weekly_review:portfolio:{today()}" in approved,
                "body": {
                    "holdings": portfolio_review.get("holdings"),
                    "opportunity_changes": portfolio_review.get("opportunity_changes"),
                    "risk_evolution": portfolio_review.get("risk_evolution"),
                },
                "issues_recommendations": False,
                "recommendation_policy": "no_allocation_advice",
            }
        )

    return {
        "as_of": now_iso(),
        "publication_types": list(PUBLICATION_TYPES),
        "n": len(pipeline),
        "rejected_n": len(rejected),
        "publications": pipeline,
        "rejected": rejected,
        "policy": "qa_pass_required_then_governance_approval",
        "issues_recommendations": False,
    }
