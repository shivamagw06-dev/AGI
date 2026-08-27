"""Canonical knowledge-object schema for AGI Finance Academy."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


ACADEMY_VERSION = "academy-v1.2.0"
COURSE_ID = "mankiw_principles_of_economics"
COURSE_TITLE = "Principles of Economics (Gregory Mankiw)"
COURSE_EDITION = "7e"

# Multi-course Academy — additional course ids live under academy/<course>/
ACCOUNTING_COURSE_ID = "damodaran_minimalist_accounting"
ACCOUNTING_COURSE_TITLE = "Minimalist Accounting (Aswath Damodaran)"
ACF_COURSE_ID = "damodaran_applied_corporate_finance"
ACF_COURSE_TITLE = "Applied Corporate Finance (Aswath Damodaran)"


INDUSTRIES = [
    "Banks",
    "Insurance",
    "IT",
    "Software",
    "Steel",
    "Power",
    "Utilities",
    "Retail",
    "Healthcare",
    "Telecom",
    "Real Estate",
    "Infrastructure",
    "FMCG",
    "Chemicals",
    "Auto",
    "Defence",
    "Logistics",
    "Shipping",
]

FOCUS_COMPANIES = [
    "Infosys",
    "Reliance",
    "HDFC Bank",
    "Tata Steel",
    "Asian Paints",
    "UltraTech",
]


@dataclass
class SourceRef:
    book: str = COURSE_TITLE
    edition: str = COURSE_EDITION
    chapter: int | None = None
    chapter_title: str | None = None
    section: str | None = None
    printed_page: int | None = None
    pdf_page: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Relationships:
    parent: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    opposing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeObject:
    """Institutional curriculum object — not a chapter summary."""

    concept: str
    concept_id: str
    definition: str
    purpose: str
    first_principles: list[str]
    formula: str | None = None
    variables: dict[str, str] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    relationships: Relationships = field(default_factory=Relationships)
    causes: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    industry_impact: dict[str, str] = field(default_factory=dict)
    company_impact: dict[str, str] = field(default_factory=dict)
    investment_impact: list[str] = field(default_factory=list)
    valuation_impact: dict[str, str] = field(default_factory=dict)
    forecast_impact: list[str] = field(default_factory=list)
    risk_impact: dict[str, Any] = field(default_factory=dict)
    decision_framework: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    questions_agi_should_answer: list[str] = field(default_factory=list)
    explainability: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.85
    sources: list[SourceRef] = field(default_factory=list)
    version: str = ACADEMY_VERSION
    status: str = "published"  # draft | reviewed | published | rejected
    mental_models: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    # Optional multi-course / accounting-curriculum fields (additive; defaults keep v1.0 objects valid)
    course_id: str = ""
    business_meaning: str = ""
    accounting_meaning: str = ""
    industry_variations: dict[str, str] = field(default_factory=dict)
    red_flags: list[str] = field(default_factory=list)
    management_decisions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["relationships"] = self.relationships.to_dict()
        d["sources"] = [s.to_dict() if isinstance(s, SourceRef) else s for s in self.sources]
        return d


@dataclass
class MentalModel:
    model_id: str
    name: str
    statement: str
    application: list[str]
    related_concepts: list[str] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    version: str = ACADEMY_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sources"] = [s.to_dict() if isinstance(s, SourceRef) else s for s in self.sources]
        return d


@dataclass
class CausalModel:
    model_id: str
    name: str
    chain: list[str]
    trigger: str
    direction: str  # increase | decrease | mixed
    industries_affected: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    version: str = ACADEMY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
