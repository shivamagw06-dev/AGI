"""Institutional catalyst catalog — company / sector / macro / market templates."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Sector → default company catalyst overlays
_SECTOR_COMPANY: dict[str, list[dict[str, Any]]] = {
    "banks": [
        {
            "id": "quarterly_earnings",
            "label": "Quarterly earnings",
            "category": "company",
            "event": "Q earnings",
            "condition": "Loan growth / NIM / credit cost vs base path",
            "impact": "strengthens_bull",
            "impact_label": "Strengthens Bull Scenario when growth & NIM beat base",
            "priority": "High",
            "probability": 0.85,
            "monitoring_source": "earnings_calendar",
        },
        {
            "id": "management_guidance",
            "label": "Management guidance",
            "category": "company",
            "event": "Guidance revision",
            "condition": "Guidance cut on loan growth or NIM",
            "impact": "strengthens_bear",
            "impact_label": "Strengthens Bear Scenario",
            "priority": "High",
            "probability": 0.45,
            "monitoring_source": "management_commentary",
        },
        {
            "id": "asset_quality_print",
            "label": "Asset-quality print",
            "category": "company",
            "event": "Credit cost / GNPA",
            "condition": "Credit cost > 0.8%",
            "impact": "strengthens_bear",
            "impact_label": "Bear stronger / Base weakened",
            "priority": "Critical",
            "probability": 0.35,
            "monitoring_source": "earnings",
        },
    ],
    "it_services": [
        {
            "id": "quarterly_earnings",
            "label": "Quarterly earnings",
            "category": "company",
            "event": "Q earnings",
            "condition": "Revenue growth > 15% (or CC growth > 6%)",
            "impact": "strengthens_bull",
            "impact_label": "Strengthens Bull Scenario",
            "priority": "High",
            "probability": 0.8,
            "monitoring_source": "earnings_calendar",
        },
        {
            "id": "large_deal_wins",
            "label": "Large deal wins",
            "category": "company",
            "event": "Mega-deal / TCV win",
            "condition": "Material large-deal conversion announced",
            "impact": "strengthens_bull",
            "impact_label": "Bull stronger",
            "priority": "High",
            "probability": 0.4,
            "monitoring_source": "corporate_announcements",
        },
        {
            "id": "weak_guidance",
            "label": "Weak guidance",
            "category": "company",
            "event": "Guidance cut",
            "condition": "CC growth guidance cut below base",
            "impact": "strengthens_bear",
            "impact_label": "Bear stronger",
            "priority": "High",
            "probability": 0.4,
            "monitoring_source": "management_commentary",
        },
        {
            "id": "margin_expansion",
            "label": "Margin expansion",
            "category": "company",
            "event": "EBIT margin print",
            "condition": "EBIT margin expands QoQ with stable utilization",
            "impact": "strengthens_bull",
            "impact_label": "Bull stronger",
            "priority": "Medium",
            "probability": 0.45,
            "monitoring_source": "earnings",
        },
        {
            "id": "ceo_change",
            "label": "CEO / leadership change",
            "category": "company",
            "event": "Leadership transition",
            "condition": "Unexpected CEO change",
            "impact": "invalidates_base",
            "impact_label": "Base Case requires review",
            "priority": "Critical",
            "probability": 0.15,
            "monitoring_source": "corporate_announcements",
        },
    ],
    "fmcg": [
        {
            "id": "quarterly_earnings",
            "label": "Quarterly earnings",
            "category": "company",
            "event": "Q earnings",
            "condition": "Volume growth > 7%",
            "impact": "strengthens_bull",
            "impact_label": "Bull stronger",
            "priority": "High",
            "probability": 0.75,
            "monitoring_source": "earnings_calendar",
        },
        {
            "id": "input_cost_spike",
            "label": "Input-cost spike",
            "category": "company",
            "event": "Gross margin pressure",
            "condition": "Gross margin contracts sharply",
            "impact": "strengthens_bear",
            "impact_label": "Bear manufacturing/FMCG stronger",
            "priority": "High",
            "probability": 0.4,
            "monitoring_source": "earnings",
        },
    ],
}

_GENERIC_COMPANY = [
    {
        "id": "quarterly_earnings",
        "label": "Quarterly earnings",
        "category": "company",
        "event": "Q earnings",
        "condition": "Material beat/miss vs institutional base path",
        "impact": "strengthens_bull",
        "impact_label": "Scenario reassessment on print",
        "priority": "High",
        "probability": 0.8,
        "monitoring_source": "earnings_calendar",
    },
    {
        "id": "buyback",
        "label": "Buyback",
        "category": "company",
        "event": "Share buyback",
        "condition": "Board-approved buyback announced",
        "impact": "strengthens_bull",
        "impact_label": "Bull stronger (capital return)",
        "priority": "Medium",
        "probability": 0.25,
        "monitoring_source": "corporate_actions",
    },
    {
        "id": "dividend_increase",
        "label": "Dividend increase",
        "category": "company",
        "event": "Dividend hike",
        "condition": "Dividend raised vs prior year",
        "impact": "strengthens_base",
        "impact_label": "Base confidence improves",
        "priority": "Medium",
        "probability": 0.35,
        "monitoring_source": "corporate_actions",
    },
    {
        "id": "acquisition",
        "label": "Acquisition",
        "category": "company",
        "event": "M&A announcement",
        "condition": "Material acquisition announced",
        "impact": "invalidates_base",
        "impact_label": "Base Case requires review",
        "priority": "Critical",
        "probability": 0.2,
        "monitoring_source": "corporate_announcements",
    },
    {
        "id": "regulatory_approval",
        "label": "Regulatory approval",
        "category": "company",
        "event": "Regulatory clearance",
        "condition": "Material approval received",
        "impact": "strengthens_bull",
        "impact_label": "Bull stronger",
        "priority": "High",
        "probability": 0.3,
        "monitoring_source": "regulatory",
    },
]

SECTOR_CATALYSTS: dict[str, list[dict[str, Any]]] = {
    "banks": [
        {
            "id": "credit_growth_cycle",
            "label": "System credit growth",
            "category": "sector",
            "event": "Credit growth print",
            "condition": "System credit growth re-accelerates",
            "impact": "strengthens_bull",
            "impact_label": "Bull banks stronger",
            "priority": "High",
            "probability": 0.55,
            "monitoring_source": "sector_data",
        },
        {
            "id": "unsecured_stress",
            "label": "Unsecured stress",
            "category": "sector",
            "event": "Retail unsecured stress",
            "condition": "Sector credit costs rise broadly",
            "impact": "strengthens_bear",
            "impact_label": "Bear banks stronger",
            "priority": "Critical",
            "probability": 0.3,
            "monitoring_source": "sector_data",
        },
    ],
    "it_services": [
        {
            "id": "ai_spending",
            "label": "AI spending increases",
            "category": "sector",
            "event": "Enterprise AI budgets",
            "condition": "Sustained AI deal momentum across peers",
            "impact": "strengthens_bull",
            "impact_label": "Bull IT stronger",
            "priority": "High",
            "probability": 0.5,
            "monitoring_source": "sector_data",
        },
        {
            "id": "demand_recovery",
            "label": "Demand recovery",
            "category": "sector",
            "event": "Discretionary IT spend",
            "condition": "Peer CC growth re-acceleration",
            "impact": "strengthens_bull",
            "impact_label": "Bull IT stronger",
            "priority": "High",
            "probability": 0.45,
            "monitoring_source": "sector_data",
        },
        {
            "id": "pricing_pressure",
            "label": "Pricing changes",
            "category": "sector",
            "event": "Pricing pressure",
            "condition": "Sector-wide pricing compression",
            "impact": "strengthens_bear",
            "impact_label": "Bear IT stronger",
            "priority": "High",
            "probability": 0.35,
            "monitoring_source": "sector_data",
        },
    ],
    "fmcg": [
        {
            "id": "commodity_inflation",
            "label": "Commodity inflation",
            "category": "sector",
            "event": "Input cost inflation",
            "condition": "Oil/agri costs rise sharply",
            "impact": "strengthens_bear",
            "impact_label": "Bear manufacturing/FMCG stronger",
            "priority": "High",
            "probability": 0.4,
            "monitoring_source": "commodity_prices",
        },
        {
            "id": "rural_demand",
            "label": "Demand recovery",
            "category": "sector",
            "event": "Rural demand",
            "condition": "Rural volume recovery confirmed",
            "impact": "strengthens_bull",
            "impact_label": "Bull FMCG stronger",
            "priority": "High",
            "probability": 0.5,
            "monitoring_source": "sector_data",
        },
    ],
}

MACRO_CATALYSTS: list[dict[str, Any]] = [
    {
        "id": "rbi_policy",
        "label": "RBI monetary policy",
        "category": "macro",
        "event": "RBI Rate Cut",
        "condition": "25bps or more",
        "impact": "strengthens_bull",
        "impact_label": "Bullish for Banks",
        "priority": "Critical",
        "probability": 0.55,
        "monitoring_source": "rbi_calendar",
        "affected_sectors": ["banks", "fmcg"],
    },
    {
        "id": "inflation",
        "label": "Inflation print",
        "category": "macro",
        "event": "CPI inflation",
        "condition": "CPI surprises vs RBI comfort band",
        "impact": "neutral",
        "impact_label": "Scenario path depends on policy reaction",
        "priority": "High",
        "probability": 0.7,
        "monitoring_source": "macro_calendar",
    },
    {
        "id": "gdp",
        "label": "GDP print",
        "category": "macro",
        "event": "GDP growth",
        "condition": "Growth materially above/below base",
        "impact": "strengthens_base",
        "impact_label": "Base path confirmation/challenge",
        "priority": "Medium",
        "probability": 0.65,
        "monitoring_source": "macro_calendar",
    },
    {
        "id": "bond_yields",
        "label": "Bond yields",
        "category": "macro",
        "event": "G-Sec yield move",
        "condition": "Yields jump > 25bps in a month",
        "impact": "strengthens_bear",
        "impact_label": "Valuation / financials pressure",
        "priority": "High",
        "probability": 0.4,
        "monitoring_source": "rates",
    },
    {
        "id": "currency",
        "label": "Currency",
        "category": "macro",
        "event": "INR move",
        "condition": "Material INR depreciation vs USD",
        "impact": "strengthens_bull",
        "impact_label": "Bull IT (translation) / Bear import-cost FMCG",
        "priority": "High",
        "probability": 0.5,
        "monitoring_source": "fx",
    },
    {
        "id": "union_budget",
        "label": "Union Budget",
        "category": "macro",
        "event": "Budget",
        "condition": "Material tax / incentive changes",
        "impact": "invalidates_base",
        "impact_label": "Base Case sector paths may need refresh",
        "priority": "Critical",
        "probability": 0.9,
        "monitoring_source": "budget_calendar",
    },
    {
        "id": "tax_changes",
        "label": "Tax changes",
        "category": "macro",
        "event": "Tax policy",
        "condition": "Corporate/sector tax regime change",
        "impact": "invalidates_base",
        "impact_label": "Thesis tax assumptions under review",
        "priority": "High",
        "probability": 0.25,
        "monitoring_source": "regulatory",
    },
]

MARKET_CATALYSTS: list[dict[str, Any]] = [
    {
        "id": "nifty_valuation",
        "label": "NIFTY valuation",
        "category": "market",
        "event": "Index valuation regime",
        "condition": "NIFTY PE moves to extreme percentile",
        "impact": "weakens_bull",
        "impact_label": "Bull harder to underwrite at extreme valuations",
        "priority": "Medium",
        "probability": 0.4,
        "monitoring_source": "market_data",
    },
    {
        "id": "liquidity",
        "label": "Liquidity",
        "category": "market",
        "event": "System liquidity",
        "condition": "Sustained liquidity tightening",
        "impact": "strengthens_bear",
        "impact_label": "Risk appetite / multiples pressure",
        "priority": "High",
        "probability": 0.35,
        "monitoring_source": "market_data",
    },
    {
        "id": "fii_flows",
        "label": "FII flows",
        "category": "market",
        "event": "Foreign flows",
        "condition": "Persistent FII selling streak",
        "impact": "strengthens_bear",
        "impact_label": "Market / beta pressure",
        "priority": "Medium",
        "probability": 0.45,
        "monitoring_source": "market_data",
    },
    {
        "id": "volatility",
        "label": "Volatility",
        "category": "market",
        "event": "Vol spike",
        "condition": "India VIX regime shift higher",
        "impact": "strengthens_bear",
        "impact_label": "Stress probability mass rises",
        "priority": "Medium",
        "probability": 0.4,
        "monitoring_source": "market_data",
    },
    {
        "id": "market_breadth",
        "label": "Market breadth",
        "category": "market",
        "event": "Breadth deterioration",
        "condition": "Advance-decline / participation narrows",
        "impact": "weakens_bull",
        "impact_label": "Bull less supported by market internals",
        "priority": "Low",
        "probability": 0.4,
        "monitoring_source": "market_data",
    },
]

# Explicit company overlays for institutional demos (INFY etc.)
COMPANY_OVERLAYS: dict[str, dict[str, Any]] = {
    "INFY": {
        "sector": "it_services",
        "name": "Infosys",
        "expected_date_hints": {
            "quarterly_earnings": "next earnings window",
            "large_deal_wins": "ongoing",
            "weak_guidance": "next earnings window",
        },
    },
    "TCS": {"sector": "it_services", "name": "Tata Consultancy Services"},
    "HDFCBANK": {"sector": "banks", "name": "HDFC Bank"},
    "KOTAKBANK": {"sector": "banks", "name": "Kotak Mahindra Bank"},
    "NESTLEIND": {"sector": "fmcg", "name": "Nestlé India"},
    "RELIANCE": {"sector": "energy", "name": "Reliance Industries"},
}


def sector_for_ticker(ticker: str, fie_profile: dict[str, Any] | None = None) -> str:
    t = (ticker or "").upper()
    if fie_profile and fie_profile.get("sector"):
        return str(fie_profile["sector"])
    overlay = COMPANY_OVERLAYS.get(t) or {}
    return str(overlay.get("sector") or "general")


def company_catalyst_templates(ticker: str, sector: str) -> list[dict[str, Any]]:
    rows = deepcopy(_SECTOR_COMPANY.get(sector) or [])
    seen = {r["id"] for r in rows}
    for g in _GENERIC_COMPANY:
        if g["id"] not in seen:
            rows.append(deepcopy(g))
    overlay = COMPANY_OVERLAYS.get((ticker or "").upper()) or {}
    hints = overlay.get("expected_date_hints") or {}
    for r in rows:
        r["entity"] = (ticker or "").upper()
        r["entity_name"] = overlay.get("name") or (ticker or "").upper()
        if r["id"] in hints:
            r["expected_date"] = hints[r["id"]]
        else:
            r.setdefault("expected_date", "calendar-dependent")
    return rows


def sector_catalyst_templates(sector: str) -> list[dict[str, Any]]:
    rows = deepcopy(SECTOR_CATALYSTS.get(sector) or [])
    for r in rows:
        r["entity"] = sector
        r["entity_name"] = sector.replace("_", " ").title()
        r.setdefault("expected_date", "ongoing / next print")
    return rows
