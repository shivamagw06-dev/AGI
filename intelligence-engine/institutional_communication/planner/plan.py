"""Communication planner — audience/purpose/template only; no reasoning."""

from __future__ import annotations

from typing import Any

from institutional_communication.schema import TEMPLATES


_INTENT_TEMPLATE: dict[str, str] = {
    "Explain": "educational",
    "Education": "educational",
    "Compare": "comparison",
    "Analyse": "company_analysis",
    "Valuation": "company_analysis",
    "Industry": "industry_analysis",
    "Macro": "macro_analysis",
    "Government": "government_analysis",
    "HistoricalReplay": "historical_replay",
    "Portfolio": "portfolio_review",
    "Documents": "research_note",
    "CrossDomain": "investment_committee_brief",
    "Accounting": "educational",
    "Risk": "research_note",
    "CorporateEvents": "research_note",
}


def plan_communication(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    intent = str(institutional_answer.get("intent_v2") or "Unknown")
    qtype = str(institutional_answer.get("question_type") or "")
    as_of = institutional_answer.get("as_of")
    concept = bool(institutional_answer.get("concept_mode"))

    template = _INTENT_TEMPLATE.get(intent, "research_note")
    if as_of or intent == "HistoricalReplay":
        template = "historical_replay"
    elif intent == "CrossDomain" and not concept:
        template = "investment_committee_brief"
    elif intent == "Analyse" and concept:
        template = "research_note"

    if template not in TEMPLATES:
        template = "research_note"

    # Densities — deterministic from evidence/framework richness
    n_ev = len(((institutional_answer.get("evidence") or {}).get("items") or []))
    n_fw = len(((institutional_answer.get("frameworks") or {}).get("framework_ids") or []))
    evidence_density = "high" if n_ev >= 6 else "moderate" if n_ev >= 2 else "low"
    citation_density = "high" if n_ev >= 4 else "moderate" if n_ev >= 1 else "low"
    detail = "deep" if template in {"investment_committee_brief", "company_analysis"} else "standard"

    audience = (
        "investment_committee"
        if template == "investment_committee_brief"
        else "institutional_analyst"
        if template in {"company_analysis", "research_note", "comparison"}
        else "portfolio_manager"
        if template in {"macro_analysis", "government_analysis", "portfolio_review"}
        else "analyst_education"
    )

    return {
        "stage": "communication_planner",
        "audience": audience,
        "purpose": f"Communicate existing institutional answer for intent={intent}",
        "question_type": qtype or intent.lower(),
        "intent_v2": intent,
        "template": template,
        "required_detail": detail,
        "narrative_style": "institutional_analyst",
        "evidence_density": evidence_density,
        "citation_density": citation_density,
        "concept_mode": concept,
        "as_of": as_of,
        "framework_count": n_fw,
        "evidence_count": n_ev,
        "fabricated": False,
        "reasoning_changed": False,
    }
