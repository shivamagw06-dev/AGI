"""Academy Books V3 — institutional knowledge object schemas (not PDF storage)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

BOOKS_V3_VERSION = "academy-books-v3.0.0"


@dataclass
class ConceptCard:
    concept_id: str
    name: str
    definition: str
    purpose: str = ""
    business_meaning: str = ""
    financial_meaning: str = ""
    investment_meaning: str = ""
    indicators: list[str] = field(default_factory=list)
    evidence_required: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    counter_examples: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    related_frameworks: list[str] = field(default_factory=list)
    related_formulas: list[str] = field(default_factory=list)
    analysts_using: list[str] = field(default_factory=list)
    source_authors: list[str] = field(default_factory=list)
    source_books: list[str] = field(default_factory=list)
    difficulty: str = "intermediate"
    confidence: float = 0.85
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FrameworkCard:
    framework_id: str
    name: str
    purpose: str
    creator: str = ""
    objective: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    decision_logic: list[str] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    counter_examples: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    related_frameworks: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    analysts_using: list[str] = field(default_factory=list)
    source_authors: list[str] = field(default_factory=list)
    confidence: float = 0.88
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FormulaCard:
    formula_id: str
    name: str
    expression: str
    purpose: str
    variables: dict[str, str] = field(default_factory=dict)
    interpretation: str = ""
    good_range: str = ""
    bad_range: str = ""
    sector_adjustments: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    related_frameworks: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CaseStudy:
    case_id: str
    company: str
    industry: str
    situation: str
    framework_applied: list[str] = field(default_factory=list)
    decision: str = ""
    outcome: str = ""
    why_it_worked: str = ""
    why_it_failed: str = ""
    lessons: list[str] = field(default_factory=list)
    related_companies: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    case_type: str = "success"  # success | failure | mixed
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FailurePattern:
    failure_id: str
    name: str
    domains: list[str] = field(default_factory=list)  # business|financial|valuation|management|macro|risk
    lessons: list[str] = field(default_factory=list)
    warning_signals: list[str] = field(default_factory=list)
    similar_companies: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MentalModelCard:
    model_id: str
    name: str
    definition: str
    purpose: str = ""
    questions: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    counter_examples: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionTree:
    tree_id: str
    name: str
    purpose: str = ""
    root: str = ""
    nodes: list[dict[str, Any]] = field(default_factory=list)
    leaves: dict[str, str] = field(default_factory=dict)
    related_concepts: list[str] = field(default_factory=list)
    analysts_using: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReasoningChain:
    chain_id: str
    name: str
    purpose: str = ""
    steps: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    analysts_using: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Checklist:
    checklist_id: str
    name: str
    domain: str  # business|financial|valuation|management|risk|macro|portfolio
    items: list[str] = field(default_factory=list)
    analysts_using: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionRule:
    rule_id: str
    name: str
    if_conditions: list[str] = field(default_factory=list)
    then_action: str = ""
    domain: str = "financial"
    related_frameworks: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    analysts_using: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuthorPerspective:
    topic_id: str
    topic: str
    perspectives: list[dict[str, str]] = field(default_factory=list)  # author, view
    agreements: list[str] = field(default_factory=list)
    disagreements: list[str] = field(default_factory=list)
    unified_institutional_view: str = ""
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SectorKnowledge:
    sector_id: str
    name: str
    business: list[str] = field(default_factory=list)
    financial: list[str] = field(default_factory=list)
    valuation: list[str] = field(default_factory=list)
    risk: list[str] = field(default_factory=list)
    macro: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    kpis: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PatternCard:
    pattern_id: str
    name: str
    definition: str = ""
    recognition_signals: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    related_frameworks: list[str] = field(default_factory=list)
    analysts_using: list[str] = field(default_factory=list)
    example_companies: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChapterKnowledge:
    """Structured chapter extraction — never raw PDF text."""

    chapter_id: str
    book_id: str
    title: str
    summary: str = ""
    purpose: str = ""
    core_concepts: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    decision_rules: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    counter_examples: list[str] = field(default_factory=list)
    case_studies: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    when_to_apply: list[str] = field(default_factory=list)
    when_not_to_apply: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    related_chapters: list[str] = field(default_factory=list)
    related_books: list[str] = field(default_factory=list)
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphLink:
    edge_id: str
    source: str
    target: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InstitutionalKnowledgeObject:
    """Unified cross-book synthesis object (one topic, many authors)."""

    object_id: str
    topic: str
    unified_definition: str
    synthesis: str
    source_authors: list[str] = field(default_factory=list)
    source_books: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    decision_rules: list[str] = field(default_factory=list)
    reasoning_chains: list[str] = field(default_factory=list)
    cases: list[str] = field(default_factory=list)
    mental_models: list[str] = field(default_factory=list)
    checklists: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    counter_examples: list[str] = field(default_factory=list)
    analysts: list[str] = field(default_factory=list)
    confidence: float = 0.9
    version: str = BOOKS_V3_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
