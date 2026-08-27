"""Universal Provider Registry — every knowledge source, registered once.

UKO reuses the KUL provider implementations so there is a single source of
truth for consult() behaviour. This module adds the capability matrix the
planner and coverage suite need: entity types, question types, authority,
freshness and expected role in the dependency graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from knowledge_unification.registry import KnowledgeRegistry, get_registry


@dataclass(frozen=True)
class ProviderCapability:
    id: str
    name: str
    priority: int
    entity_types: tuple[str, ...]
    question_types: tuple[str, ...]
    authority: str          # market | consensus | institutional | pedagogical | warehouse
    freshness: str          # live | daily | batch | static
    role: str               # identity | industry | business | financials | valuation |
                            # investment | portfolio | research | memory | pedagogy
    required_for: tuple[str, ...] = ()  # question families that must consult this
    status: str = "active"


# Capability matrix. Ids must match KUL ProviderSpec.id values.
CAPABILITIES: dict[str, ProviderCapability] = {
    "historical_intelligence": ProviderCapability(
        id="historical_intelligence",
        name="Historical Intelligence Engine",
        priority=6,
        entity_types=("company",),
        question_types=("historical", "company", "valuation", "financials", "investment"),
        authority="warehouse",
        freshness="daily",
        role="research",
        required_for=("historical",),
    ),
    "historical_valuation_intelligence": ProviderCapability(
        id="historical_valuation_intelligence",
        name="Historical Valuation Intelligence Engine",
        priority=5,
        entity_types=("company",),
        question_types=("historical", "valuation", "company", "attribution", "investment"),
        authority="warehouse",
        freshness="daily",
        role="valuation",
        required_for=("historical", "valuation", "attribution"),
    ),
    "unified_valuation_engine": ProviderCapability(
        id="unified_valuation_engine",
        name="Unified Valuation Engine",
        priority=5,
        entity_types=("company",),
        question_types=("valuation", "company", "investment", "comparison"),
        authority="warehouse",
        freshness="daily",
        role="valuation",
        required_for=("valuation", "company_intel", "comparison"),
    ),
    "valuation_attribution_engine": ProviderCapability(
        id="valuation_attribution_engine",
        name="Valuation Attribution Engine",
        priority=5,
        entity_types=("company",),
        question_types=("attribution", "valuation", "company", "investment"),
        authority="institutional",
        freshness="daily",
        role="valuation",
        required_for=("attribution", "valuation"),
    ),
    "valuation_policy_engine": ProviderCapability(
        id="valuation_policy_engine",
        name="Valuation Policy Engine",
        priority=6,
        entity_types=("company",),
        question_types=("valuation", "company", "attribution"),
        authority="institutional",
        freshness="daily",
        role="valuation",
        required_for=("valuation", "attribution"),
    ),
    "market_intelligence_engine": ProviderCapability(
        id="market_intelligence_engine",
        name="Market & Sector Intelligence",
        priority=4,
        entity_types=("market", "sector", "company"),
        question_types=("market", "macro", "screen", "investment"),
        authority="market",
        freshness="daily",
        role="investment",
        required_for=("market", "macro", "screen"),
    ),
    "research_intelligence_engine": ProviderCapability(
        id="research_intelligence_engine",
        name="Research Intelligence Engine",
        priority=4,
        entity_types=("company",),
        question_types=("research", "company", "investment", "valuation", "forecast"),
        authority="institutional",
        freshness="daily",
        role="research",
        required_for=("research", "company_intel", "comparison"),
    ),
    "forecast_intelligence_engine": ProviderCapability(
        id="forecast_intelligence_engine",
        name="Forecast Intelligence Engine",
        priority=4,
        entity_types=("company",),
        question_types=("forecast", "company", "investment", "macro"),
        authority="institutional",
        freshness="daily",
        role="research",
        required_for=("forecast", "company_intel"),
    ),
    "macro_intelligence_engine": ProviderCapability(
        id="macro_intelligence_engine",
        name="Macro Intelligence Engine",
        priority=3,
        entity_types=("macro", "sector", "company"),
        question_types=("macro", "forecast", "market", "company"),
        authority="institutional",
        freshness="daily",
        role="research",
        required_for=("macro", "market", "forecast"),
    ),
    "institutional_warehouse": ProviderCapability(
        id="institutional_warehouse",
        name="Institutional Data Warehouse",
        priority=8,
        entity_types=("company",),
        question_types=("company", "valuation", "financials", "investment", "market", "screen"),
        authority="warehouse",
        freshness="daily",
        role="financials",
        required_for=("company", "valuation", "financials", "investment"),
    ),
    "capiq_ikt": ProviderCapability(
        id="capiq_ikt",
        name="CapIQ Institutional Knowledge Tables",
        priority=20,
        entity_types=("company",),
        question_types=("company", "business_model", "market", "valuation", "industry"),
        authority="institutional",
        freshness="batch",
        role="identity",
        required_for=("company", "business", "valuation"),
    ),
    "industry_intelligence": ProviderCapability(
        id="industry_intelligence",
        name="Industry Intelligence",
        priority=22,
        entity_types=("company", "industry"),
        question_types=("industry", "business_model", "valuation", "company"),
        authority="institutional",
        freshness="static",
        role="industry",
        required_for=("industry", "valuation", "business"),
    ),
    "business_intelligence": ProviderCapability(
        id="business_intelligence",
        name="Business Intelligence",
        priority=24,
        entity_types=("company",),
        question_types=("business_model", "moat", "unit_economics", "company"),
        authority="institutional",
        freshness="batch",
        role="business",
        required_for=("business", "investment"),
    ),
    "financial_statement_warehouse": ProviderCapability(
        id="financial_statement_warehouse",
        name="Financial Statement Warehouse",
        priority=21,
        entity_types=("company",),
        question_types=("financials", "valuation", "company", "accounting"),
        authority="warehouse",
        freshness="batch",
        role="financials",
        required_for=("financials", "valuation"),
    ),
    "financial_statement_intelligence": ProviderCapability(
        id="financial_statement_intelligence",
        name="Financial Statement Intelligence",
        priority=40,
        entity_types=("company", "concept"),
        question_types=("accounting", "financials", "concept"),
        authority="pedagogical",
        freshness="static",
        role="pedagogy",
    ),
    "financial_foundations": ProviderCapability(
        id="financial_foundations",
        name="Financial Foundations",
        priority=42,
        entity_types=("concept",),
        question_types=("accounting", "concept"),
        authority="pedagogical",
        freshness="static",
        role="pedagogy",
    ),
    "financial_concepts": ProviderCapability(
        id="financial_concepts",
        name="Financial Concepts",
        priority=44,
        entity_types=("concept",),
        question_types=("concept", "valuation", "accounting"),
        authority="pedagogical",
        freshness="static",
        role="pedagogy",
    ),
    "valuation_terminal": ProviderCapability(
        id="valuation_terminal",
        name="Valuation Terminal",
        priority=18,
        entity_types=("company", "industry"),
        question_types=("valuation", "company", "market", "investment"),
        authority="market",
        freshness="daily",
        role="valuation",
        required_for=("valuation",),
    ),
    "valuation_consensus": ProviderCapability(
        id="valuation_consensus",
        name="Capital IQ Consensus",
        priority=19,
        entity_types=("company",),
        question_types=("valuation", "consensus", "company", "investment"),
        authority="consensus",
        freshness="batch",
        role="valuation",
        required_for=("valuation", "consensus"),
    ),
    "hedge_fund_screens": ProviderCapability(
        id="hedge_fund_screens",
        name="Hedge Fund Strategy Screens",
        priority=26,
        entity_types=("company",),
        question_types=("investment", "valuation", "portfolio", "market"),
        authority="institutional",
        freshness="daily",
        role="investment",
    ),
    "investment_intelligence": ProviderCapability(
        id="investment_intelligence",
        name="Investment Intelligence",
        priority=25,
        entity_types=("company",),
        question_types=("investment", "thesis", "company"),
        authority="institutional",
        freshness="batch",
        role="investment",
        required_for=("investment",),
    ),
    "portfolio_intelligence": ProviderCapability(
        id="portfolio_intelligence",
        name="Portfolio Intelligence",
        priority=28,
        entity_types=("portfolio", "company"),
        question_types=("portfolio", "investment"),
        authority="institutional",
        freshness="batch",
        role="portfolio",
        required_for=("portfolio",),
    ),
    "research_intelligence": ProviderCapability(
        id="research_intelligence",
        name="Research Intelligence",
        priority=27,
        entity_types=("company",),
        question_types=("research", "company", "investment"),
        authority="institutional",
        freshness="batch",
        role="research",
        required_for=("research",),
    ),
    "company_memory": ProviderCapability(
        id="company_memory",
        name="Company Memory",
        priority=30,
        entity_types=("company",),
        question_types=("company", "business_model", "investment"),
        authority="institutional",
        freshness="batch",
        role="memory",
    ),
    "ikl": ProviderCapability(
        id="ikl",
        name="Institutional Knowledge Layer",
        priority=32,
        entity_types=("company", "industry", "macro"),
        question_types=("company", "industry", "macro", "investment"),
        authority="institutional",
        freshness="batch",
        role="memory",
    ),
    "knowledge_factory": ProviderCapability(
        id="knowledge_factory",
        name="Knowledge Factory",
        priority=34,
        entity_types=("company", "industry", "macro"),
        question_types=("company", "industry", "macro"),
        authority="institutional",
        freshness="batch",
        role="memory",
    ),
    "cgl": ProviderCapability(
        id="cgl",
        name="Continuous Gather & Learn",
        priority=36,
        entity_types=("company", "industry", "macro"),
        question_types=("company", "research", "market"),
        authority="institutional",
        freshness="live",
        role="memory",
    ),
    "academy": ProviderCapability(
        id="academy",
        name="Finance Academy",
        priority=50,
        entity_types=("concept",),
        question_types=("concept", "accounting", "macro"),
        authority="pedagogical",
        freshness="static",
        role="pedagogy",
    ),
    "legacy_kip": ProviderCapability(
        id="legacy_kip",
        name="Legacy KIP Corpus",
        priority=55,
        entity_types=("company", "document"),
        question_types=("research", "company"),
        authority="institutional",
        freshness="batch",
        role="research",
    ),
}


# Dependency order the planner respects when ranking providers.
DEPENDENCY_ORDER: tuple[str, ...] = (
    "identity",
    "industry",
    "business",
    "financials",
    "valuation",
    "investment",
    "portfolio",
    "research",
    "memory",
    "pedagogy",
)


def provider_ids() -> list[str]:
    return sorted(CAPABILITIES)


def capability(provider_id: str) -> Optional[ProviderCapability]:
    return CAPABILITIES.get(provider_id)


def kul_registry() -> KnowledgeRegistry:
    """The single consult() registry — KUL owns the implementations."""
    return get_registry()


def registered_providers() -> list[dict[str, Any]]:
    """Capability matrix joined with live KUL health."""
    reg = kul_registry()
    out: list[dict[str, Any]] = []
    for pid, cap in CAPABILITIES.items():
        provider = reg.get(pid)
        health = "unregistered"
        if provider is not None:
            try:
                health = provider.health_check()
            except Exception as exc:
                health = f"error:{type(exc).__name__}"
        out.append(
            {
                "id": cap.id,
                "name": cap.name,
                "priority": cap.priority,
                "entity_types": list(cap.entity_types),
                "question_types": list(cap.question_types),
                "authority": cap.authority,
                "freshness": cap.freshness,
                "role": cap.role,
                "required_for": list(cap.required_for),
                "status": "active" if provider is not None else "missing_implementation",
                "health": health,
            }
        )
    return out
