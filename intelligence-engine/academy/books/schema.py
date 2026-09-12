"""Schemas for Academy book ingestion → structured knowledge objects."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


BOOKS_VERSION = "academy-books-v2.0.0"

ACADEMY_TAXONOMY = (
    "accounting",
    "valuation",
    "corporate_finance",
    "economics",
    "investment",
    "behavioural_finance",
    "risk_management",
    "portfolio_management",
    "macro",
    "sector_banking",
    "sector_it_services",
    "sector_fmcg",
    "sector_pharma",
    "sector_insurance",
    "sector_energy",
    "sector_infrastructure",
    "sector_real_estate",
    "sector_telecom",
    "sector_automobiles",
    "sector_metals",
    "sector_capital_goods",
    "sector_chemicals",
    "sector_consumer_durables",
)

# Hard caps — never retain copyrighted long form
MAX_DEFINITION_CHARS = 280
MAX_EXPLANATION_CHARS = 480
MAX_EXAMPLE_CHARS = 220
MAX_VERBATIM_REJECT = 800  # any extracted span longer than this is discarded


@dataclass
class BookMeta:
    book_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    edition: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    language: str = "en"
    subject: str | None = None
    topics: list[str] = field(default_factory=list)
    difficulty: str = "intermediate"  # intro | intermediate | advanced
    source_format: str = "seed"  # pdf | epub | docx | markdown | seed
    version: int = 1
    status: str = "published"
    academies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChapterNode:
    node_id: str
    book_id: str
    title: str
    level: str  # part | chapter | section | subsection
    order: int = 0
    parent_id: str | None = None
    summary: str = ""  # AGI-owned short summary only

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FormulaObject:
    formula_id: str
    name: str
    expression: str
    explanation: str
    variables: dict[str, str] = field(default_factory=dict)
    use_cases: list[str] = field(default_factory=list)
    academy: str = "valuation"
    source_book_id: str | None = None
    source_chapter: str | None = None
    confidence: float = 0.8
    version: str = BOOKS_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FrameworkObject:
    framework_id: str
    name: str
    purpose: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    decision_logic: list[str] = field(default_factory=list)
    applications: list[str] = field(default_factory=list)
    academy: str = "investment"
    related_concepts: list[str] = field(default_factory=list)
    source_book_id: str | None = None
    source_chapter: str | None = None
    confidence: float = 0.85
    version: str = BOOKS_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BookConcept:
    """AGI-owned concept extracted or seeded from institutional books."""

    concept_id: str
    title: str
    definition: str
    explanation: str = ""
    examples: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    linked_formulas: list[str] = field(default_factory=list)
    linked_frameworks: list[str] = field(default_factory=list)
    linked_companies: list[str] = field(default_factory=list)
    linked_industries: list[str] = field(default_factory=list)
    academy: str = "investment"
    difficulty: str = "intermediate"
    confidence: float = 0.8
    source_book_id: str | None = None
    source_chapter: str | None = None
    version: str = BOOKS_VERSION
    kind: str = "concept"  # concept | principle | mental_model | terminology

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GraphEdge:
    edge_id: str
    source: str
    target: str
    relation: str  # related | depends_on | applies_to | measures | framework_of
    weight: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
