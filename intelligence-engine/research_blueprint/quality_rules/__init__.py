"""Quality rules — max sections/tables/charts, citations, evidence, style."""

from __future__ import annotations

from typing import Any


def build_quality_rules(report_type: str, bp_meta: dict[str, Any]) -> dict[str, Any]:
    style = bp_meta.get("output_style") or "institutional_memo"
    citation = "required" if report_type not in {"educational_guide", "market_open_brief", "market_close_brief"} else "recommended"
    evidence_min = 5
    if report_type == "educational_guide":
        evidence_min = 2
    elif report_type in {"institutional_investment_report", "investment_committee_memo"}:
        evidence_min = 8
    elif report_type in {"news_brief", "market_open_brief", "market_close_brief"}:
        evidence_min = 3

    return {
        "maximum_sections": int(bp_meta.get("max_sections") or 12),
        "maximum_tables": int(bp_meta.get("max_tables") or 5),
        "maximum_charts": int(bp_meta.get("max_charts") or 4),
        "maximum_length_words": int(bp_meta.get("max_length_words") or 2500),
        "citation_rules": citation,
        "evidence_requirements": {
            "minimum_independent_evidence": evidence_min,
            "prefer_tier1_sources": True,
        },
        "writing_style": style,
        "report_type": report_type,
    }
