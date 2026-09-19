"""AGIB Phase 2.6 — Institutional Financial Concepts, core schema.

A deterministic knowledge layer, not a retrieval or LLM-prompt project.
Every ``ConceptCard`` below is authored, textbook-grounded content —
``evidence_level`` and ``confidence`` describe how well-established the
concept is (all are institutional-finance/GAAP/IFRS standard material, not
extracted from any live document), never a claim about a specific company.

This package deliberately does NOT duplicate financial_foundations (Phase 1:
accounting mechanics) or financial_statement_intelligence (Phase 2: analyst
interpretation of a specific company's numbers). It answers "what is X /
why does X matter" for the vocabulary an equity analyst uses every day —
corporate finance, valuation, banking, credit, and market concepts that
neither earlier phase covers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FC_VERSION = "financial-concepts-v1.0.0"
PROGRAMME = "AGIB Phase 2.6 — Institutional Financial Concepts"
MODULE_CODE = "FC"

FREEZE_LOCKS: dict[str, Any] = {
    "not_a_recommendation_engine": True,
    "no_retrieval_dependency": True,
    "no_llm_dependency": True,
    "deterministic_only": True,
    "no_company_specific_analysis": True,
    "fabricated": False,
}

MODULES: tuple[str, ...] = (
    "corporate_finance",
    "ratio_intelligence",
    "valuation",
    "banking",
    "cash_flow",
    "capital_allocation",
    "credit",
    "market",
    "business_quality",
)

EVIDENCE_LEVELS: tuple[str, ...] = (
    "textbook",         # standard corporate-finance / CFA-curriculum material
    "gaap_ifrs",        # accounting-standard-defined term
    "market_convention", # widely used market/analyst convention, not a single standard body
    "regulatory",        # defined by a banking/market regulator (RBI, Basel, SEBI, etc.)
)


@dataclass(frozen=True)
class ConceptCard:
    key: str
    module: str
    title: str
    definition: str
    business_meaning: str
    interpretation: str = ""
    formula: str = ""
    common_mistakes: str = ""
    industry_exceptions: str = ""
    related_concepts: tuple[str, ...] = field(default_factory=tuple)
    evidence_level: str = "textbook"
    confidence: float = 0.95

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "module": self.module,
            "title": self.title,
            "definition": self.definition,
            "formula": self.formula or None,
            "business_meaning": self.business_meaning,
            "interpretation": self.interpretation,
            "common_mistakes": self.common_mistakes or None,
            "industry_exceptions": self.industry_exceptions or None,
            "related_concepts": list(self.related_concepts),
            "evidence_level": self.evidence_level,
            "confidence": self.confidence,
            "fabricated": False,
        }
