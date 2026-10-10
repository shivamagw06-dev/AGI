"""Quality control before knowledge publication."""

from __future__ import annotations

from typing import Any

from academy.catalog import all_knowledge_objects
from academy.schema import KnowledgeObject


REQUIRED_FIELDS = (
    "concept",
    "definition",
    "purpose",
    "first_principles",
    "relationships",
    "causes",
    "effects",
    "industry_impact",
    "company_impact",
    "investment_impact",
    "valuation_impact",
    "forecast_impact",
    "risk_impact",
    "decision_framework",
    "sources",
)


def _weak_definition(definition: str) -> bool:
    text = (definition or "").strip()
    if len(text) < 40:
        return True
    banned = ("see chapter", "summary of", "this chapter discusses")
    return any(b in text.lower() for b in banned)


def review_object(ko: KnowledgeObject) -> dict[str, Any]:
    issues: list[str] = []
    d = ko.to_dict()
    for field in REQUIRED_FIELDS:
        val = d.get(field)
        if val is None or val == "" or val == [] or val == {}:
            issues.append(f"missing:{field}")
    if _weak_definition(ko.definition):
        issues.append("weak_definition")
    if not ko.relationships.related and not ko.relationships.children and not ko.relationships.parent:
        issues.append("missing_relationships")
    if not ko.sources:
        issues.append("missing_sources")
    if ko.confidence < 0.5:
        issues.append("low_confidence")
    if not ko.investment_impact:
        issues.append("missing_investment_implications")
    status = "rejected" if issues else "reviewed"
    return {
        "concept_id": ko.concept_id,
        "course_id": ko.course_id,
        "status": status,
        "issues": issues,
        "publishable": not issues,
    }


def review_corpus(course_id: str | None = None) -> dict[str, Any]:
    objs = all_knowledge_objects(course_id)
    reviews = [review_object(o) for o in objs]
    by_name: dict[str, list[str]] = {}
    for o in objs:
        key = o.concept.strip().lower()
        by_name.setdefault(key, []).append(o.concept_id)
    duplicates = {k: v for k, v in by_name.items() if len(v) > 1}
    rejected = [r for r in reviews if not r["publishable"]]
    return {
        "reviewed": len(reviews),
        "publishable": sum(1 for r in reviews if r["publishable"]),
        "rejected": rejected,
        "duplicates": duplicates,
        "passed": not rejected and not duplicates,
        "reviews": reviews,
        "course_id": course_id or "all",
    }
