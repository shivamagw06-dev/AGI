"""Institutional evidence-backed relationship catalog — Sprint 8.3.

Every entry includes supporting historical evidence. Nothing is inferred
without an evidence record (historical cycles / timeline anchors / financial periods).
"""

from __future__ import annotations

from typing import Any

from app.contracts.models import (
    RelationshipConfidence,
    RelationshipDomain,
    RelationshipType,
)


def _ev(kind: str, summary: str, *, period: str | None = None, refs: list[str] | None = None, weight: float = 1.0) -> dict[str, Any]:
    return {
        "kind": kind,
        "summary": summary,
        "period": period,
        "source_refs": refs or [],
        "weight": weight,
    }


# Company structural / competitive relationships
COMPANY_RELATIONSHIP_CATALOG: list[dict[str, Any]] = [
    {
        "domain": RelationshipDomain.COMPANY.value,
        "source_key": "INFY",
        "source_label": "Infosys",
        "target_key": "TCS",
        "target_label": "TCS",
        "relationship_type": RelationshipType.COMPETITOR.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 12,
        "average_delay": None,
        "first_observed": "2008",
        "last_confirmed": "2025",
        "chain": [],
        "evidence": [
            _ev(
                "institutional_catalog",
                "Infosys and TCS compete for large enterprise IT / digital deals in overlapping verticals",
                period="2008-2025",
                refs=["timeline:INFY:2008:Global Financial Crisis", "timeline:TCS:2008:Global Financial Crisis"],
                weight=1.5,
            ),
            _ev(
                "historical_cycle",
                "Both names show correlated margin and deal-cycle stress in 2022–2023 slowdown",
                period="2022-2023",
                refs=["timeline:INFY:2022:Margin Compression", "timeline:TCS:2022:Deal Slowdown"],
                weight=1.2,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.COMPANY.value,
        "source_key": "INFY",
        "source_label": "Infosys",
        "target_key": "accenture",
        "target_label": "Accenture",
        "relationship_type": RelationshipType.GLOBAL_PEER.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 10,
        "first_observed": "2014",
        "last_confirmed": "2025",
        "evidence": [
            _ev(
                "institutional_catalog",
                "Accenture is the primary global peer for Indian IT services pricing and AI deal framing",
                period="2014-2025",
                refs=["timeline:INFY:2025:AI Transformation"],
                weight=1.4,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.COMPANY.value,
        "source_key": "INFY",
        "source_label": "Infosys",
        "target_key": "USD",
        "target_label": "USD",
        "relationship_type": RelationshipType.REVENUE_SENSITIVITY.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 15,
        "average_delay": "1 Quarter",
        "first_observed": "2008",
        "last_confirmed": "2025",
        "evidence": [
            _ev(
                "financial_period",
                "Majority of Infosys revenue denominated in USD; INR moves transmit to reported growth",
                period="FY2015-FY2025",
                refs=["hko:INFY:financials:annual"],
                weight=1.5,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.COMPANY.value,
        "source_key": "ai_spending",
        "source_label": "AI Spending",
        "target_key": "INFY",
        "target_label": "Infosys",
        "relationship_type": RelationshipType.DEMAND_DRIVER.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 4,
        "first_observed": "2023",
        "last_confirmed": "2025",
        "chain": ["information_technology", "enterprise_ai"],
        "evidence": [
            _ev(
                "timeline_link",
                "Sector AI spending boom transmits into Infosys AI transformation agenda",
                period="2023-2025",
                refs=[
                    "timeline:information_technology:2023:AI Spending Boom",
                    "timeline:INFY:2025:AI Transformation",
                ],
                weight=1.5,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.COMPANY.value,
        "source_key": "TCS",
        "source_label": "TCS",
        "target_key": "INFY",
        "target_label": "Infosys",
        "relationship_type": RelationshipType.SECTOR_PEER.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 12,
        "first_observed": "2008",
        "last_confirmed": "2025",
        "evidence": [
            _ev(
                "institutional_catalog",
                "TCS and Infosys are core Nifty IT peer set for relative valuation and deal wins",
                period="2008-2025",
                refs=["entity:INFY:sector:information_technology", "entity:TCS:sector:information_technology"],
                weight=1.3,
            ),
        ],
    },
]

# Sector relationships
SECTOR_RELATIONSHIP_CATALOG: list[dict[str, Any]] = [
    {
        "domain": RelationshipDomain.SECTOR.value,
        "source_key": "information_technology",
        "source_label": "IT Services",
        "target_key": "us_technology_spending",
        "target_label": "US Technology Spending",
        "relationship_type": RelationshipType.DEMAND_DRIVER.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 10,
        "first_observed": "2008",
        "last_confirmed": "2025",
        "evidence": [
            _ev(
                "historical_cycle",
                "Indian IT revenue growth historically tracks US tech / discretionary IT budgets",
                period="2008-2025",
                refs=["timeline:information_technology:2008:Financial Crisis", "timeline:information_technology:2020:COVID Demand Surge"],
                weight=1.5,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.SECTOR.value,
        "source_key": "information_technology",
        "source_label": "IT Services",
        "target_key": "USDINR",
        "target_label": "USDINR",
        "relationship_type": RelationshipType.REVENUE_SENSITIVITY.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 14,
        "average_delay": "1 Quarter",
        "first_observed": "2013",
        "last_confirmed": "2025",
        "evidence": [
            _ev(
                "historical_cycle",
                "INR depreciation historically supports reported INR margins/revenue for IT exporters",
                period="2013-2025",
                refs=["timeline:india:2013:Taper Tantrum / INR Stress"],
                weight=1.4,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.SECTOR.value,
        "source_key": "digital_transformation",
        "source_label": "Digital Transformation",
        "target_key": "information_technology",
        "target_label": "IT Services",
        "relationship_type": RelationshipType.SECTOR_BENEFICIARY.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 6,
        "first_observed": "2014",
        "last_confirmed": "2023",
        "chain": ["enterprise_ai"],
        "evidence": [
            _ev(
                "timeline_link",
                "2014 digital transformation wave and later AI budgets lifted IT Services demand",
                period="2014-2023",
                refs=[
                    "timeline:information_technology:2014:Digital Transformation",
                    "timeline:information_technology:2023:AI Spending Boom",
                ],
                weight=1.4,
            ),
        ],
    },
]

# Macro causal chains — the core of HRI before pattern engines
MACRO_RELATIONSHIP_CATALOG: list[dict[str, Any]] = [
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "rbi_rate_cut",
        "source_label": "RBI Rate Cut",
        "target_key": "HDFCBANK",
        "target_label": "HDFC Bank",
        "relationship_type": RelationshipType.POSITIVE_HISTORICAL_IMPACT.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 8,
        "average_delay": "3 Trading Days",
        "first_observed": "2015",
        "last_confirmed": "2025",
        "chain": [
            "Lower borrowing costs",
            "Bank lending improves",
            "Private Banks outperform",
            "Housing demand increases",
            "Auto financing improves",
        ],
        "evidence": [
            _ev(
                "historical_cycle",
                "Across multiple RBI easing cycles, private banks including HDFC Bank historically outperformed on NIM/volume expectations",
                period="2015-2025",
                refs=["timeline:HDFCBANK:2022:Rate-Hike NIM Cycle", "timeline:india:2020:COVID Policy Response", "timeline:india:2025:Rate-Cut Optionality"],
                weight=1.8,
            ),
            _ev(
                "institutional_catalog",
                "Transmission path: rate cut → lower borrowing costs → lending / housing / auto finance → private bank earnings sensitivity",
                period="2015-2025",
                refs=["macro:rbi_rate_cycle", "sector:financials", "sector:housing", "sector:autos"],
                weight=1.5,
            ),
            _ev(
                "timeline_link",
                "COVID policy response and 2025 rate-cut optionality anchors remain on India macro timeline",
                period="2020-2025",
                refs=["timeline:india:2020:COVID Policy Response", "timeline:india:2025:Rate-Cut Optionality"],
                weight=1.2,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "rbi_rate_cut",
        "source_label": "RBI Rate Cut",
        "target_key": "banks",
        "target_label": "Banks",
        "relationship_type": RelationshipType.POSITIVE_HISTORICAL_IMPACT.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 10,
        "average_delay": "2 Trading Days",
        "first_observed": "2015",
        "last_confirmed": "2025",
        "chain": ["Lower borrowing costs", "Bank lending improves"],
        "evidence": [
            _ev(
                "historical_cycle",
                "Bank Nifty historically responds positively in early RBI easing windows",
                period="2015-2025",
                refs=["macro:rbi_rate_cycle", "sector:financials"],
                weight=1.6,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "rbi_rate_cut",
        "source_label": "RBI Rate Cut",
        "target_key": "housing",
        "target_label": "Housing",
        "relationship_type": RelationshipType.BENEFICIARY.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 7,
        "average_delay": "1-2 Quarters",
        "first_observed": "2015",
        "last_confirmed": "2025",
        "chain": ["Lower borrowing costs", "Housing demand increases"],
        "evidence": [
            _ev(
                "historical_cycle",
                "Mortgage rate transmission historically lifts housing demand with a lag after RBI cuts",
                period="2015-2025",
                refs=["macro:rbi_rate_cycle", "sector:housing"],
                weight=1.4,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "rbi_rate_cut",
        "source_label": "RBI Rate Cut",
        "target_key": "autos",
        "target_label": "Autos",
        "relationship_type": RelationshipType.BENEFICIARY.value,
        "confidence": RelationshipConfidence.MEDIUM.value,
        "occurrences": 6,
        "average_delay": "1-2 Quarters",
        "first_observed": "2015",
        "last_confirmed": "2025",
        "chain": ["Auto financing improves"],
        "evidence": [
            _ev(
                "historical_cycle",
                "Auto financing affordability improves after easing; demand recovery historically lags cuts",
                period="2015-2025",
                refs=["macro:rbi_rate_cycle", "sector:autos"],
                weight=1.2,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "higher_crude_oil",
        "source_label": "Higher Crude Oil",
        "target_key": "paints",
        "target_label": "Paint Companies",
        "relationship_type": RelationshipType.NEGATIVE_HISTORICAL_IMPACT.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 6,
        "average_delay": "1 Quarter",
        "first_observed": "2014",
        "last_confirmed": "2022",
        "chain": [],
        "evidence": [
            _ev(
                "historical_cycle",
                "Crude-linked input costs historically pressure paint company gross margins",
                period="2014-2022",
                refs=["timeline:energy:2014:Oil Price Collapse", "timeline:energy:2022:Energy Inflation Spike"],
                weight=1.4,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "higher_crude_oil",
        "source_label": "Higher Crude Oil",
        "target_key": "airlines",
        "target_label": "Airlines",
        "relationship_type": RelationshipType.NEGATIVE_HISTORICAL_IMPACT.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 8,
        "average_delay": "Days to Weeks",
        "first_observed": "2014",
        "last_confirmed": "2022",
        "evidence": [
            _ev(
                "historical_cycle",
                "Jet fuel is a dominant airline cost; crude spikes historically compress airline margins",
                period="2014-2022",
                refs=["timeline:energy:2022:Energy Inflation Spike"],
                weight=1.5,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "higher_crude_oil",
        "source_label": "Higher Crude Oil",
        "target_key": "omcs",
        "target_label": "OMCs",
        "relationship_type": RelationshipType.UNDER_PRESSURE.value,
        "confidence": RelationshipConfidence.MEDIUM.value,
        "occurrences": 7,
        "first_observed": "2014",
        "last_confirmed": "2022",
        "evidence": [
            _ev(
                "historical_cycle",
                "OMCs face marketing margin / under-recovery pressure when crude rises faster than retail pass-through",
                period="2014-2022",
                refs=["timeline:energy:2022:Energy Inflation Spike"],
                weight=1.3,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MACRO.value,
        "source_key": "higher_crude_oil",
        "source_label": "Higher Crude Oil",
        "target_key": "upstream_energy",
        "target_label": "Upstream Energy",
        "relationship_type": RelationshipType.POSITIVE_HISTORICAL_IMPACT.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 9,
        "first_observed": "2014",
        "last_confirmed": "2022",
        "evidence": [
            _ev(
                "historical_cycle",
                "Upstream producers historically benefit from higher realized crude prices",
                period="2014-2022",
                refs=["timeline:energy:2022:Energy Inflation Spike", "entity:RELIANCE"],
                weight=1.5,
            ),
        ],
    },
]

# Market relationships (Budget / liquidity transmission)
MARKET_RELATIONSHIP_CATALOG: list[dict[str, Any]] = [
    {
        "domain": RelationshipDomain.MARKET.value,
        "source_key": "budget",
        "source_label": "Budget",
        "target_key": "capital_goods",
        "target_label": "Capital Goods",
        "relationship_type": RelationshipType.BENEFICIARY.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 6,
        "first_observed": "2016",
        "last_confirmed": "2024",
        "chain": ["Railways", "Infrastructure"],
        "evidence": [
            _ev(
                "historical_cycle",
                "Capex-heavy Union Budgets historically lift capital goods / railways / infrastructure narratives",
                period="2016-2024",
                refs=["timeline:india:2024:Union Budget / Fiscal Stance", "timeline:nifty:2024:Election Cycle"],
                weight=1.5,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MARKET.value,
        "source_key": "rbi",
        "source_label": "RBI",
        "target_key": "liquidity",
        "target_label": "Liquidity",
        "relationship_type": RelationshipType.TRANSMISSION.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 12,
        "first_observed": "2016",
        "last_confirmed": "2025",
        "chain": ["Banks", "Autos", "Real Estate", "Consumption"],
        "evidence": [
            _ev(
                "historical_cycle",
                "RBI liquidity stance transmits through banks into rate-sensitive consumption sectors",
                period="2016-2025",
                refs=["timeline:nifty:2021:Liquidity Rally", "timeline:india:2020:COVID Policy Response"],
                weight=1.6,
            ),
        ],
    },
    {
        "domain": RelationshipDomain.MARKET.value,
        "source_key": "liquidity",
        "source_label": "Liquidity",
        "target_key": "banks",
        "target_label": "Banks",
        "relationship_type": RelationshipType.POSITIVE_HISTORICAL_IMPACT.value,
        "confidence": RelationshipConfidence.HIGH.value,
        "occurrences": 10,
        "first_observed": "2020",
        "last_confirmed": "2021",
        "chain": ["Autos", "Real Estate", "Consumption"],
        "evidence": [
            _ev(
                "timeline_link",
                "2021 liquidity rally followed COVID policy response — banks as primary transmission node",
                period="2020-2021",
                refs=["timeline:nifty:2021:Liquidity Rally", "timeline:india:2020:COVID Policy Response"],
                weight=1.4,
            ),
        ],
    },
]


def all_catalog_entries() -> list[dict[str, Any]]:
    return (
        list(COMPANY_RELATIONSHIP_CATALOG)
        + list(SECTOR_RELATIONSHIP_CATALOG)
        + list(MACRO_RELATIONSHIP_CATALOG)
        + list(MARKET_RELATIONSHIP_CATALOG)
    )
