"""Retrieval policies — what KRIG fetches for each query type."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QueryType(str, Enum):
    COMPANY = "company"
    SECTOR = "sector"
    MACRO = "macro"
    MARKET = "market"
    PORTFOLIO = "portfolio"
    COMPARE = "compare"
    BUNDLE = "bundle"


class BundleSection(str, Enum):
    COMPANY = "company"
    FINANCIALS = "financials"
    VALUATION = "valuation"
    CORPORATE_EVENTS = "corporate_events"
    SECTOR = "sector"
    MARKET = "market"
    MACRO = "macro"
    EVIDENCE = "evidence"
    LEARNING = "learning"
    RELATIONSHIPS = "relationships"
    MONITORING = "monitoring"
    MEMORY = "memory"
    TIMELINE = "timeline"
    CONFLICTS = "conflicts"


@dataclass(frozen=True)
class RetrievalPolicy:
    query_type: QueryType
    sections: tuple[BundleSection, ...]
    cache_ttl_seconds: int = 300
    description: str = ""


COMPANY_POLICY = RetrievalPolicy(
    query_type=QueryType.COMPANY,
    sections=(
        BundleSection.COMPANY,
        BundleSection.FINANCIALS,
        BundleSection.VALUATION,
        BundleSection.CORPORATE_EVENTS,
        BundleSection.MONITORING,
        BundleSection.TIMELINE,
        BundleSection.MEMORY,
        BundleSection.LEARNING,
        BundleSection.RELATIONSHIPS,
        BundleSection.SECTOR,
        BundleSection.MARKET,
        BundleSection.EVIDENCE,
        BundleSection.CONFLICTS,
    ),
    cache_ttl_seconds=300,
    description="Company institutional context for Ask / judgment",
)

SECTOR_POLICY = RetrievalPolicy(
    query_type=QueryType.SECTOR,
    sections=(
        BundleSection.SECTOR,
        BundleSection.LEARNING,
        BundleSection.MARKET,
        BundleSection.EVIDENCE,
    ),
    cache_ttl_seconds=300,
    description="Sector object, leaders, risks, sector learning",
)

MACRO_POLICY = RetrievalPolicy(
    query_type=QueryType.MACRO,
    sections=(
        BundleSection.MACRO,
        BundleSection.MARKET,
        BundleSection.LEARNING,
        BundleSection.EVIDENCE,
    ),
    cache_ttl_seconds=180,
    description="RBI, inflation, GDP, policy, historical cycles",
)

MARKET_POLICY = RetrievalPolicy(
    query_type=QueryType.MARKET,
    sections=(BundleSection.MARKET, BundleSection.MACRO, BundleSection.LEARNING),
    cache_ttl_seconds=60,
    description="Market regime + breadth tips",
)

PORTFOLIO_POLICY = RetrievalPolicy(
    query_type=QueryType.PORTFOLIO,
    sections=(
        BundleSection.COMPANY,
        BundleSection.LEARNING,
        BundleSection.MEMORY,
        BundleSection.MONITORING,
        BundleSection.TIMELINE,
        BundleSection.EVIDENCE,
    ),
    cache_ttl_seconds=300,
    description="Thesis / decision / monitoring oriented bundle",
)

COMPARE_POLICY = RetrievalPolicy(
    query_type=QueryType.COMPARE,
    sections=COMPANY_POLICY.sections,
    cache_ttl_seconds=300,
    description="Multi-company comparison with shared sector/macro",
)

POLICIES: dict[QueryType, RetrievalPolicy] = {
    QueryType.COMPANY: COMPANY_POLICY,
    QueryType.SECTOR: SECTOR_POLICY,
    QueryType.MACRO: MACRO_POLICY,
    QueryType.MARKET: MARKET_POLICY,
    QueryType.PORTFOLIO: PORTFOLIO_POLICY,
    QueryType.COMPARE: COMPARE_POLICY,
    QueryType.BUNDLE: COMPANY_POLICY,
}


def policy_for(query_type: QueryType | str) -> RetrievalPolicy:
    if isinstance(query_type, str):
        query_type = QueryType(query_type)
    return POLICIES[query_type]
