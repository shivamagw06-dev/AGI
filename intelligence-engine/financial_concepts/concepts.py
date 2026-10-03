"""Master concept library — aggregates every module's cards into one index.

This is the single source of truth Module 9 (relationships), Module 10/13
(the library itself), and Module 11 (Ask routing) all read from.
"""

from __future__ import annotations

from financial_concepts.concepts_banking import BANKING_CONCEPTS
from financial_concepts.concepts_business_quality import BUSINESS_QUALITY_CONCEPTS
from financial_concepts.concepts_capital_allocation import CAPITAL_ALLOCATION_CONCEPTS
from financial_concepts.concepts_cash_flow import CASH_FLOW_CONCEPTS
from financial_concepts.concepts_corporate_actions import CORPORATE_ACTIONS_CONCEPTS
from financial_concepts.concepts_corporate_finance import CORPORATE_FINANCE_CONCEPTS
from financial_concepts.concepts_credit import CREDIT_CONCEPTS
from financial_concepts.concepts_investing_philosophy import INVESTING_PHILOSOPHY_CONCEPTS
from financial_concepts.concepts_market import MARKET_CONCEPTS
from financial_concepts.concepts_ratio_intelligence import RATIO_INTELLIGENCE_CONCEPTS
from financial_concepts.concepts_reporting_metrics import REPORTING_METRICS_CONCEPTS
from financial_concepts.concepts_valuation import VALUATION_CONCEPTS
from financial_concepts.schema import ConceptCard

_SOURCE_DICTS: tuple[dict[str, ConceptCard], ...] = (
    CORPORATE_FINANCE_CONCEPTS,
    RATIO_INTELLIGENCE_CONCEPTS,
    VALUATION_CONCEPTS,
    BANKING_CONCEPTS,
    CASH_FLOW_CONCEPTS,
    CAPITAL_ALLOCATION_CONCEPTS,
    CREDIT_CONCEPTS,
    MARKET_CONCEPTS,
    BUSINESS_QUALITY_CONCEPTS,
    CORPORATE_ACTIONS_CONCEPTS,
    INVESTING_PHILOSOPHY_CONCEPTS,
    REPORTING_METRICS_CONCEPTS,
)

ALL_CONCEPTS: dict[str, ConceptCard] = {}
for _d in _SOURCE_DICTS:
    for _k, _v in _d.items():
        if _k in ALL_CONCEPTS:
            raise ValueError(f"Duplicate concept key across modules: {_k!r}")
        ALL_CONCEPTS[_k] = _v


def all_concept_keys() -> list[str]:
    return sorted(ALL_CONCEPTS.keys())


def get_concept(key: str) -> ConceptCard | None:
    return ALL_CONCEPTS.get(key)


def concepts_by_module(module: str) -> dict[str, ConceptCard]:
    return {k: v for k, v in ALL_CONCEPTS.items() if v.module == module}


def concept_count() -> int:
    return len(ALL_CONCEPTS)


def concept_count_by_module() -> dict[str, int]:
    out: dict[str, int] = {}
    for card in ALL_CONCEPTS.values():
        out[card.module] = out.get(card.module, 0) + 1
    return out


def validate_related_concepts() -> list[str]:
    """Every related_concepts reference must point at a real key — this is
    run as a test to guarantee Module 9's graph has no dangling edges."""

    errors = []
    for key, card in ALL_CONCEPTS.items():
        for related in card.related_concepts:
            if related not in ALL_CONCEPTS:
                errors.append(f"{key} references unknown related concept {related!r}")
    return errors
