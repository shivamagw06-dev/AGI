"""Module 2 — Structured Knowledge Builder.

Scans Module 1 paragraphs for the 15 institutional knowledge categories and
turns matching paragraphs into evidence-backed :class:`~kip_v2.schema.Fact`
objects (category, key, value=snippet text, confidence, evidence). Every
object is independent — a company can have many ``risks`` facts, many
``products`` facts, etc. Nothing is stored here directly; callers pass the
returned facts through ``storage.store_fact`` (which re-applies the Module 7
gate) so this module never needs to know about persistence.
"""

from __future__ import annotations

from typing import Iterable

from kip_v2.schema import Evidence, Fact, KNOWLEDGE_CATEGORIES, Paragraph

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "business_model": ("business model", "our business", "we operate", "core business", "revenue model"),
    "products": ("our products", "product portfolio", "product range", "product line", "flagship product"),
    "segments": ("reportable segment", "business segment", "operating segment", "segment revenue"),
    "revenue_drivers": ("revenue growth", "driven by", "growth was led by", "key growth driver", "revenue driver", "volume growth"),
    "cost_drivers": ("cost of", "increase in cost", "cost driver", "raw material cost", "input cost", "cost pressure"),
    "customers": ("our customers", "key customers", "customer base", "clientele", "top customers"),
    "suppliers": ("our suppliers", "key suppliers", "supply chain", "vendor base", "raw material sourcing"),
    "competition": ("competitors", "competitive landscape", "market share", "competition from", "competitive intensity"),
    "management": ("board of directors", "management team", "chief executive", "managing director", "leadership team", "appointed as"),
    "risks": ("risk factor", "risks and concerns", "principal risks", "material risk", "key risk"),
    "strategy": ("our strategy", "strategic priorities", "growth strategy", "strategic initiative", "medium-term strategy"),
    "capital_allocation": ("capital allocation", "capex plan", "capital expenditure", "dividend policy", "buyback"),
    "mna": ("acquisition of", "merger with", "joint venture", "divestment", "stake sale", "acquired"),
    "esg": ("sustainability", "carbon emission", "csr initiative", "environment, social", "renewable energy"),
    "financial_kpis": ("key performance indicator", "operating metrics", "kpi", "unit economics"),
}

assert set(CATEGORY_KEYWORDS) == set(KNOWLEDGE_CATEGORIES)


def _confidence(hits: int, section_match: bool) -> float:
    base = 0.45 + 0.12 * hits
    if section_match:
        base += 0.15
    return round(min(0.95, base), 3)


_SECTION_HINTS: dict[str, tuple[str, ...]] = {
    "business_model": ("business_overview",),
    "risks": ("risk_factors",),
    "segments": ("segment_information",),
    "strategy": ("strategy_outlook",),
    "capital_allocation": ("capital_allocation",),
    "management": ("management_commentary", "corporate_governance"),
    "esg": ("esg",),
    "mna": ("mna",),
}


def classify_paragraph(paragraph: Paragraph) -> list[tuple[str, float, int]]:
    """Returns [(category, confidence, keyword_hits), ...] for every category
    whose keywords match this paragraph's text."""

    low = paragraph.text.lower()
    matches: list[tuple[str, float, int]] = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in low)
        if hits == 0:
            continue
        section_match = paragraph.section in _SECTION_HINTS.get(category, ())
        matches.append((category, _confidence(hits, section_match), hits))
    return matches


def build_knowledge_facts(company_id: str, paragraphs: Iterable[Paragraph], period: str | None = None) -> list[Fact]:
    facts: list[Fact] = []
    for paragraph in paragraphs:
        for category, confidence, hits in classify_paragraph(paragraph):
            evidence = Evidence(
                document_id=paragraph.document_id,
                page=paragraph.page,
                paragraph_id=paragraph.paragraph_id,
                snippet=paragraph.text[:500],
            )
            fact_id = Fact.make_id(company_id, category, category, period, evidence.evidence_hash)
            facts.append(
                Fact(
                    fact_id=fact_id,
                    company_id=company_id,
                    category=category,
                    key=category,
                    value=paragraph.text[:800],
                    period=period,
                    unit=None,
                    currency=None,
                    confidence=confidence,
                    evidence=evidence,
                    source_document_id=paragraph.document_id,
                    extra={"keyword_hits": hits, "section": paragraph.section},
                )
            )
    return facts
