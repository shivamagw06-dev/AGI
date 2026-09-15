"""Institutional narrative seeds — company / sector / market / macro timelines."""

from __future__ import annotations

from typing import Any

from app.contracts.models import TimelineImportance, TimelineScope

# Company narrative overlays (merged with derived events from store)
COMPANY_TIMELINE_SEEDS: dict[str, list[dict[str, Any]]] = {
    "INFY": [
        {
            "year": 1993,
            "title": "IPO",
            "description": "Infosys lists — institutional public-market chapter begins",
            "importance": TimelineImportance.CRITICAL.value,
            "event_type": "corporate",
            "links": [
                {"from_key": "INFY:1993:IPO", "to_key": "nifty:listing", "relation": "joined_market", "note": "Public equity era"}
            ],
        },
        {
            "year": 2008,
            "title": "Global Financial Crisis",
            "description": "Demand shock and pricing pressure across IT services",
            "importance": TimelineImportance.CRITICAL.value,
            "event_type": "macro_transmission",
            "links": [
                {"from_key": "macro:2008:gfc", "to_key": "information_technology:2008:Financial Crisis", "relation": "caused"},
                {"from_key": "information_technology:2008:Financial Crisis", "to_key": "INFY:2008:Global Financial Crisis", "relation": "affected"},
                {"from_key": "INFY:2008:Global Financial Crisis", "to_key": "INFY:revenue", "relation": "transmitted_to"},
            ],
        },
        {
            "year": 2014,
            "title": "Leadership Change",
            "description": "Leadership transition reshapes strategy and client engagement",
            "importance": TimelineImportance.HIGH.value,
            "event_type": "management",
        },
        {
            "year": 2020,
            "title": "COVID",
            "description": "Pandemic demand surge for digital / cloud transformation",
            "importance": TimelineImportance.CRITICAL.value,
            "event_type": "macro_transmission",
            "links": [
                {"from_key": "macro:2020:covid", "to_key": "information_technology:2020:COVID Demand Surge", "relation": "caused"},
                {"from_key": "information_technology:2020:COVID Demand Surge", "to_key": "INFY:2020:COVID", "relation": "affected"},
                {"from_key": "INFY:2020:COVID", "to_key": "INFY:revenue", "relation": "transmitted_to"},
                {"from_key": "INFY:revenue", "to_key": "INFY:margins", "relation": "transmitted_to"},
                {"from_key": "INFY:margins", "to_key": "INFY:valuation", "relation": "transmitted_to"},
            ],
        },
        {
            "year": 2022,
            "title": "Margin Compression",
            "description": "Post-pandemic deal slowdown and margin defence",
            "importance": TimelineImportance.HIGH.value,
            "event_type": "financial",
            "links": [
                {"from_key": "INFY:2022:Margin Compression", "to_key": "INFY:margins", "relation": "transmitted_to"},
                {"from_key": "INFY:margins", "to_key": "INFY:valuation", "relation": "transmitted_to"},
            ],
        },
        {
            "year": 2025,
            "title": "AI Transformation",
            "description": "AI spending and large-deal agenda redefine growth path",
            "importance": TimelineImportance.CRITICAL.value,
            "event_type": "strategic",
            "links": [
                {"from_key": "information_technology:2023:AI Spending Boom", "to_key": "INFY:2025:AI Transformation", "relation": "affected"},
            ],
        },
    ],
    "TCS": [
        {"year": 2008, "title": "Global Financial Crisis", "importance": TimelineImportance.CRITICAL.value, "event_type": "macro_transmission"},
        {"year": 2020, "title": "COVID", "importance": TimelineImportance.CRITICAL.value, "event_type": "macro_transmission"},
        {"year": 2022, "title": "Deal Slowdown", "importance": TimelineImportance.HIGH.value, "event_type": "financial"},
        {"year": 2025, "title": "AI Transformation", "importance": TimelineImportance.HIGH.value, "event_type": "strategic"},
    ],
    "HDFCBANK": [
        {"year": 2008, "title": "Global Financial Crisis", "importance": TimelineImportance.CRITICAL.value, "event_type": "macro_transmission"},
        {"year": 2018, "title": "NBFC Stress Spillover", "importance": TimelineImportance.HIGH.value, "event_type": "sector"},
        {"year": 2020, "title": "COVID Credit Uncertainty", "importance": TimelineImportance.CRITICAL.value, "event_type": "macro_transmission"},
        {"year": 2022, "title": "Rate-Hike NIM Cycle", "importance": TimelineImportance.HIGH.value, "event_type": "macro_transmission"},
    ],
    "RELIANCE": [
        {"year": 2016, "title": "Jio Disruption Era", "importance": TimelineImportance.CRITICAL.value, "event_type": "strategic"},
        {"year": 2020, "title": "COVID", "importance": TimelineImportance.HIGH.value, "event_type": "macro_transmission"},
        {"year": 2022, "title": "Energy & Retail Rebalancing", "importance": TimelineImportance.MEDIUM.value, "event_type": "strategic"},
    ],
}

SECTOR_TIMELINE_SEEDS: dict[str, list[dict[str, Any]]] = {
    "information_technology": [
        {"year": 2008, "title": "Financial Crisis", "description": "Global demand shock for IT services", "importance": TimelineImportance.CRITICAL.value},
        {"year": 2014, "title": "Digital Transformation", "description": "Shift from traditional outsourcing to digital", "importance": TimelineImportance.HIGH.value},
        {"year": 2020, "title": "COVID Demand Surge", "description": "Cloud / digital acceleration", "importance": TimelineImportance.CRITICAL.value},
        {"year": 2023, "title": "AI Spending Boom", "description": "Enterprise AI budgets become sector catalyst", "importance": TimelineImportance.CRITICAL.value},
    ],
    "financials": [
        {"year": 2008, "title": "Global Financial Crisis", "importance": TimelineImportance.CRITICAL.value},
        {"year": 2018, "title": "NBFC Stress", "importance": TimelineImportance.HIGH.value},
        {"year": 2020, "title": "COVID Credit Cycle", "importance": TimelineImportance.CRITICAL.value},
        {"year": 2022, "title": "Rate Hike Cycle", "importance": TimelineImportance.HIGH.value},
    ],
    "energy": [
        {"year": 2014, "title": "Oil Price Collapse", "importance": TimelineImportance.HIGH.value},
        {"year": 2020, "title": "COVID Demand Shock", "importance": TimelineImportance.CRITICAL.value},
        {"year": 2022, "title": "Energy Inflation Spike", "importance": TimelineImportance.HIGH.value},
    ],
}

MARKET_TIMELINE_SEEDS: list[dict[str, Any]] = [
    {"year": 2016, "title": "Demonetisation", "description": "Liquidity and consumption shock", "importance": TimelineImportance.CRITICAL.value},
    {"year": 2020, "title": "COVID Crash", "description": "Risk-off collapse then policy response", "importance": TimelineImportance.CRITICAL.value},
    {"year": 2021, "title": "Liquidity Rally", "description": "Policy-supported risk appetite", "importance": TimelineImportance.HIGH.value},
    {"year": 2022, "title": "Inflation", "description": "Global inflation and tightening", "importance": TimelineImportance.HIGH.value},
    {"year": 2024, "title": "Election Cycle", "description": "Political / policy uncertainty premium", "importance": TimelineImportance.MEDIUM.value},
]

MACRO_TIMELINE_SEEDS: list[dict[str, Any]] = [
    {"year": 2013, "title": "Taper Tantrum / INR Stress", "event_type": "currency", "importance": TimelineImportance.HIGH.value},
    {"year": 2016, "title": "Demonetisation", "event_type": "fiscal_policy", "importance": TimelineImportance.CRITICAL.value},
    {"year": 2018, "title": "NBFC Liquidity Stress", "event_type": "credit", "importance": TimelineImportance.HIGH.value},
    {"year": 2020, "title": "COVID Policy Response", "event_type": "rbi_rate_cycle", "importance": TimelineImportance.CRITICAL.value},
    {"year": 2022, "title": "Inflation Cycle", "event_type": "inflation_cycle", "importance": TimelineImportance.CRITICAL.value},
    {"year": 2023, "title": "GDP Recovery Path", "event_type": "gdp_cycle", "importance": TimelineImportance.HIGH.value},
    {"year": 2024, "title": "Union Budget / Fiscal Stance", "event_type": "budget", "importance": TimelineImportance.HIGH.value},
    {"year": 2025, "title": "Rate-Cut Optionality", "event_type": "rbi_rate_cycle", "importance": TimelineImportance.HIGH.value},
]

SCOPE_SUBJECT = {
    TimelineScope.MARKET.value: "nifty",
    TimelineScope.MACRO.value: "india",
}
