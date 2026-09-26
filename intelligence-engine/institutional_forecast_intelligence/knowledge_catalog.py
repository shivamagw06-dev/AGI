"""AGI-owned knowledge tips for IFI — never live Yahoo/NSE during forecast prep.

When HIP / KRIG are unavailable, IFI uses these institutional knowledge seeds
so Forecast Bundles remain deterministic and offline-testable.
"""

from __future__ import annotations

from typing import Any

COMPANY_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "INFY": {
        "ticker": "INFY",
        "name": "Infosys",
        "sector": "Information Technology",
        "sector_key": "information_technology",
        "business_profile": "Global IT services / digital transformation / AI services",
        "financial_quality": "High — historically strong FCF and balance sheet",
        "valuation": {"pe_tip": 24.0, "regime": "premium_to_history_mid"},
        "competitive_position": "Tier-1 Indian IT; peers TCS / Accenture",
        "investment_thesis": "AI-led large-deal cycle vs near-term demand air-pocket risk",
        "decision_status": "Monitor — prepare scenarios; no recommendation",
    },
    "TCS": {
        "ticker": "TCS",
        "name": "TCS",
        "sector": "Information Technology",
        "sector_key": "information_technology",
        "business_profile": "Largest Indian IT services franchise",
        "financial_quality": "High",
        "valuation": {"pe_tip": 28.0, "regime": "quality_premium"},
        "competitive_position": "Sector leader",
        "investment_thesis": "Franchise durability through demand cycles",
        "decision_status": "Monitor",
    },
    "HDFCBANK": {
        "ticker": "HDFCBANK",
        "name": "HDFC Bank",
        "sector": "Financials",
        "sector_key": "financials",
        "business_profile": "Leading private sector bank",
        "financial_quality": "High — liability franchise focus",
        "valuation": {"pe_tip": 18.0, "regime": "mid_cycle"},
        "competitive_position": "Private bank leader",
        "investment_thesis": "Rate-cycle transmission via NIM / volumes",
        "decision_status": "Monitor",
    },
    "RELIANCE": {
        "ticker": "RELIANCE",
        "name": "Reliance Industries",
        "sector": "Energy",
        "sector_key": "energy",
        "business_profile": "Energy, retail, digital conglomerate",
        "financial_quality": "Conglomerate — segment-dependent",
        "valuation": {"pe_tip": 22.0, "regime": "sum_of_parts"},
        "competitive_position": "Domestic conglomerate leader",
        "investment_thesis": "Energy cycle + consumer digital optionality",
        "decision_status": "Monitor",
    },
}

SECTOR_INTELLIGENCE: dict[str, dict[str, Any]] = {
    "information_technology": {
        "sector_key": "information_technology",
        "label": "IT Services",
        "outlook": "Demand mixed; AI budgets rising; traditional outsourcing slower",
        "relative_valuation": "Premium names still priced for quality",
        "competitive_landscape": "INFY / TCS / HCL / Accenture global peer set",
        "leadership_changes": "Ongoing AI org redesigns",
        "sector_learning": "COVID surge → deal slowdown → AI spending boom sequence",
        "outlook_dimensions": ["Growth Outlook", "Margin Outlook", "Deal Pipeline", "Valuation Outlook"],
    },
    "financials": {
        "sector_key": "financials",
        "label": "Banking / Financials",
        "outlook": "Rate-cut optionality supportive for volumes; NIM path mixed",
        "relative_valuation": "Private banks mid-cycle",
        "competitive_landscape": "HDFC Bank / ICICI / SBI peer set",
        "credit_cycle": "Stable with watch on unsecured",
        "outlook_dimensions": ["Growth Outlook", "Margin Outlook", "Credit Cycle", "Valuation Outlook"],
    },
    "energy": {
        "sector_key": "energy",
        "label": "Energy",
        "outlook": "Crude-linked spreads and refining/marketing dynamics",
        "relative_valuation": "Cycle-sensitive",
        "outlook_dimensions": ["Upstream", "OMC Margins", "Retail/Digital", "Valuation Outlook"],
    },
}

MARKET_INTELLIGENCE: dict[str, Any] = {
    "market": "NIFTY",
    "regime": "Late-cycle / liquidity-supported",
    "liquidity": "Adequate",
    "breadth": "Mixed — leadership concentrated",
    "valuation": "Elevated vs long-term median",
    "volatility": "Contained",
    "outlook_dimensions": ["Valuation", "Liquidity", "Breadth", "Expected Regime"],
}

MACRO_INTELLIGENCE: dict[str, Any] = {
    "region": "India",
    "inflation": {"direction": "moderating", "summary": "Disinflation supportive of easing optionality"},
    "rbi": {"stance": "Easing bias / data-dependent", "summary": "Rate-cut optionality into soft landing path"},
    "gdp": {"direction": "moderating_growth", "summary": "Domestic demand resilient; watch global spillover"},
    "currency": {"usd_inr": "elevated", "summary": "INR levels matter for IT exporters"},
    "interest_rates": {"path": "downside_bias"},
    "fiscal_policy": {"stance": "capex_supportive"},
    "outlook_dimensions": ["Inflation", "RBI", "GDP", "Currency"],
}

THEME_INTELLIGENCE: dict[str, dict[str, Any]] = {
    "artificial_intelligence": {
        "theme": "Artificial Intelligence",
        "beneficiaries": ["IT Services", "Cloud platforms", "Semiconductor supply chain"],
        "risks": ["Capex digestion", "Deal deferral", "Margin investment drag"],
        "capital_allocation": "Enterprise AI budgets rising from pilot to production",
        "sector_impact": {"information_technology": "Demand driver", "financials": "Secondary adopter"},
        "outlook_dimensions": ["Beneficiaries", "Risks", "Capital Allocation", "Sector Impact"],
    },
    "rate_cut_cycle": {
        "theme": "RBI Rate Cut Cycle",
        "beneficiaries": ["Private Banks", "Housing", "Autos", "Real Estate"],
        "risks": ["Inflation surprise", "Currency pressure"],
        "capital_allocation": "Duration / rate-sensitive equity preference historically rises",
        "sector_impact": {"financials": "Primary beneficiary", "autos": "Lagged beneficiary"},
        "outlook_dimensions": ["Beneficiaries", "Risks", "Transmission", "Sector Impact"],
    },
}

RESEARCH_TIPS: dict[str, dict[str, Any]] = {
    "INFY": {
        "company_research_office": "Near-term demand air-pocket vs AI large-deal narrative",
        "sector_research_office": "IT Services: US discretionary IT budgets cautious",
        "market_research_office": "Quality growth still bid on dips",
        "macro_research_office": "USDINR supportive for reported margins when INR soft",
        "theme_research_office": "AI transformation as multi-year demand driver",
        "as_of": "institutional_seed",
    },
    "HDFCBANK": {
        "company_research_office": "Liability franchise + rate transmission watchpoints",
        "sector_research_office": "Private banks: volume vs NIM trade-off in easing",
        "market_research_office": "Financials sensitive to RBI path",
        "macro_research_office": "Easing cycles historically support banks / housing / autos",
        "theme_research_office": "Rate-cut cycle transmission",
        "as_of": "institutional_seed",
    },
}

MONITORING_EVENTS: dict[str, list[dict[str, Any]]] = {
    "INFY": [
        {"event": "Large-deal TCV", "status": "Watching", "importance": "High"},
        {"event": "Margin commentary", "status": "Watching", "importance": "High"},
        {"event": "US financial services demand", "status": "Watching", "importance": "Medium"},
    ],
    "HDFCBANK": [
        {"event": "RBI policy decision", "status": "Scheduled", "importance": "Critical"},
        {"event": "NIM trajectory", "status": "Watching", "importance": "High"},
        {"event": "Deposit growth", "status": "Watching", "importance": "High"},
    ],
}

CATALYSTS: dict[str, list[dict[str, Any]]] = {
    "INFY": [
        {"catalyst": "AI deal conversions", "polarity": "positive", "evidence": "Theme + sector learning"},
        {"catalyst": "Prolonged client caution", "polarity": "negative", "evidence": "Sector outlook"},
    ],
    "HDFCBANK": [
        {"catalyst": "RBI rate cut", "polarity": "positive", "evidence": "Macro + historical relationships"},
        {"catalyst": "Inflation re-acceleration", "polarity": "negative", "evidence": "Macro intelligence"},
    ],
}

RISKS: dict[str, list[dict[str, Any]]] = {
    "INFY": [
        {"risk": "Demand slowdown persistence", "severity": "High"},
        {"risk": "Wage / utilisation pressure", "severity": "Medium"},
        {"risk": "USDINR reversal", "severity": "Medium"},
    ],
    "HDFCBANK": [
        {"risk": "NIM compression in deep cuts", "severity": "Medium"},
        {"risk": "Unsecured credit stress", "severity": "Medium"},
    ],
}

HISTORICAL_TIPS: dict[str, dict[str, Any]] = {
    "INFY": {
        "timelines": [
            {"year": 2020, "title": "COVID"},
            {"year": 2022, "title": "Margin Compression"},
            {"year": 2025, "title": "AI Transformation"},
        ],
        "cycles": ["Deal slowdown 2022-23", "Digital surge 2020-21"],
        "coverage": "FY2015–FY2025 financial history available in HIP when configured",
    },
    "HDFCBANK": {
        "timelines": [
            {"year": 2020, "title": "COVID Credit Uncertainty"},
            {"year": 2022, "title": "Rate-Hike NIM Cycle"},
        ],
        "cycles": ["Easing cycles historically supportive"],
        "coverage": "Rate-cycle transmission documented in HRI",
    },
}

ANALOGUE_TIPS: dict[str, list[dict[str, Any]]] = {
    "INFY": [
        {
            "matched_period": "FY2022",
            "similarity_score": 88.0,
            "label": "Margin compression / deal slowdown",
            "source": "hai_seed",
        },
        {
            "matched_period": "FY2020",
            "similarity_score": 82.0,
            "label": "COVID growth air-pocket",
            "source": "hai_seed",
        },
    ],
    "HDFCBANK": [
        {
            "matched_period": "2015-2017 easing",
            "similarity_score": 85.0,
            "label": "Prior RBI easing window",
            "source": "hai_seed",
        }
    ],
}

RELATIONSHIP_TIPS: dict[str, list[dict[str, Any]]] = {
    "INFY": [
        {"source": "AI Spending", "target": "INFY", "type": "Demand Driver", "confidence": "High"},
        {"source": "INFY", "target": "TCS", "type": "Competitor", "confidence": "High"},
        {"source": "USD", "target": "INFY", "type": "Revenue Sensitivity", "confidence": "High"},
    ],
    "HDFCBANK": [
        {
            "source": "RBI Rate Cut",
            "target": "HDFCBANK",
            "type": "Positive Historical Impact",
            "confidence": "High",
            "chain": [
                "Lower borrowing costs",
                "Bank lending improves",
                "Private Banks outperform",
                "Housing demand increases",
                "Auto financing improves",
            ],
        }
    ],
}
