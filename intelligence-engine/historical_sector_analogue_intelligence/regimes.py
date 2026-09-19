"""Historical sector regime catalogs + soft builders from CSKP / HSIP / SRI / HMIP."""

from __future__ import annotations

from typing import Any

from historical_sector_analogue_intelligence.schema import SUPPORTED_SECTORS, SectorRegime

FEATURE_UNITS: dict[str, str] = {
    "revenue_growth": "% yoy",
    "earnings_growth": "% yoy",
    "margin_profile": "% EBITDA margin",
    "roe": "% ROE",
    "valuation": "x PE",
    "relative_performance": "pp vs NIFTY",
    "interest_rate": "% repo",
    "inflation": "% CPI yoy",
    "currency": "USDINR",
    "policy": "0-10 support index",
    "industry_structure": "0-10 structure index",
}

SECTOR_KEY_MAP: dict[str, str] = {
    "Banking": "banking",
    "IT Services": "it_services",
    "FMCG": "fmcg",
    "Auto": "auto",
    "Capital Goods": "capital_goods",
    "Pharma": "pharma",
}

# Evidence-backed sector regime vectors. Fundamentals/valuation tips align with
# HSIP seeded timelines where available; macro tips align with HMIP.

SECTOR_REGIME_CATALOG: dict[str, list[dict[str, Any]]] = {
    "Banking": [
        {
            "period": "2008",
            "label": "GFC credit shock — NPA formation begins",
            "features": {
                "revenue_growth": 12.0,
                "earnings_growth": -8.0,
                "margin_profile": 3.2,
                "roe": 12.0,
                "valuation": 14.0,
                "relative_performance": -18.0,
                "interest_rate": 9.0,
                "inflation": 8.3,
                "currency": 48.0,
                "policy": 4.0,
                "industry_structure": 6.0,
            },
            "outcome": "Credit froze; NPAs rose into 2010s; policy liquidity support followed",
            "equity_outcome": "Banking underperformed; recovery lagged broader market",
            "historical_outcome_bundle": {
                "sector_return": "Deep underperformance then multi-year repair",
                "revenue_growth": "Slowing loan growth",
                "margin_trend": "NIM compressed then stabilised",
                "valuation_change": "De-rating on asset quality fear",
                "market_leadership": "PSU banks led underperformance",
                "recovery_time": "3-5 years to credit normalisation",
            },
            "timeline_refs": ["hsip:banking:FY2008", "india:2008:GFC"],
            "research_refs": ["Sector Research: Banking GFC credit shock"],
        },
        {
            "period": "2013",
            "label": "Taper / INR stress — wholesale funding pressure",
            "features": {
                "revenue_growth": 10.0,
                "earnings_growth": 4.0,
                "margin_profile": 3.0,
                "roe": 13.5,
                "valuation": 15.5,
                "relative_performance": -8.0,
                "interest_rate": 7.75,
                "inflation": 9.5,
                "currency": 68.0,
                "policy": 5.0,
                "industry_structure": 6.5,
            },
            "outcome": "Funding costs rose; private banks more resilient than wholesale-funded peers",
            "equity_outcome": "Selective private bank outperformance; weak names sold off",
            "historical_outcome_bundle": {
                "sector_return": "Mixed; quality franchises held",
                "revenue_growth": "Moderate credit growth",
                "margin_trend": "NIM pressure from funding",
                "valuation_change": "Modest de-rating",
                "market_leadership": "HDFC Bank / Kotak relative leaders",
                "recovery_time": "4-6 quarters after INR stabilisation",
            },
            "timeline_refs": ["hsip:banking:FY2013", "india:2013:Taper Tantrum"],
            "research_refs": ["Sector Research: 2013 banking funding stress"],
        },
        {
            "period": "2017",
            "label": "Post-demonetisation credit expansion window",
            "features": {
                "revenue_growth": 14.0,
                "earnings_growth": 16.0,
                "margin_profile": 3.5,
                "roe": 15.0,
                "valuation": 22.0,
                "relative_performance": 6.0,
                "interest_rate": 6.0,
                "inflation": 3.3,
                "currency": 65.0,
                "policy": 7.0,
                "industry_structure": 7.0,
            },
            "outcome": "Credit and deposit growth accelerated; housing / retail led",
            "equity_outcome": "Private banks outperformed; valuations expanded",
            "historical_outcome_bundle": {
                "sector_return": "Strong absolute and relative returns",
                "revenue_growth": "Double-digit loan growth",
                "margin_trend": "Stable-to-improving NIMs",
                "valuation_change": "Premium expansion",
                "market_leadership": "Private bank leadership solidified",
                "recovery_time": "Already mid-cycle expansion",
            },
            "timeline_refs": ["hsip:banking:FY2017", "hsip:banking:Revenue Growth"],
            "research_refs": ["Sector Research: 2017 credit expansion"],
        },
        {
            "period": "2020",
            "label": "COVID credit freeze — emergency liquidity",
            "features": {
                "revenue_growth": 6.0,
                "earnings_growth": -12.0,
                "margin_profile": 3.4,
                "roe": 9.0,
                "valuation": 16.0,
                "relative_performance": -12.0,
                "interest_rate": 4.0,
                "inflation": 6.2,
                "currency": 76.0,
                "policy": 9.0,
                "industry_structure": 6.5,
            },
            "outcome": "Moratoria + ECLGS; credit growth paused then retail rebound",
            "equity_outcome": "Sharp drawdown then liquidity rally; NBFCs lagged banks",
            "historical_outcome_bundle": {
                "sector_return": "V-shaped equity recovery",
                "revenue_growth": "Paused then retail-led rebound",
                "margin_trend": "NIM supported by low funding costs",
                "valuation_change": "Crash then re-rating",
                "market_leadership": "Well-capitalised private banks led",
                "recovery_time": "2-4 quarters for loan growth",
            },
            "timeline_refs": ["hsip:banking:FY2020", "india:2020:COVID Policy Response"],
            "research_refs": ["Sector Research: COVID banking liquidity"],
        },
        {
            "period": "2022",
            "label": "Tightening cycle — NIM expansion",
            "features": {
                "revenue_growth": 15.0,
                "earnings_growth": 22.0,
                "margin_profile": 3.8,
                "roe": 16.5,
                "valuation": 18.0,
                "relative_performance": 10.0,
                "interest_rate": 6.25,
                "inflation": 6.7,
                "currency": 82.0,
                "policy": 6.0,
                "industry_structure": 7.5,
            },
            "outcome": "NIMs expanded with rate hikes; credit growth remained healthy",
            "equity_outcome": "Banks outperformed growth assets; leadership concentrated",
            "historical_outcome_bundle": {
                "sector_return": "Relative outperformance vs NIFTY",
                "revenue_growth": "Strong NII growth",
                "margin_trend": "NIM peak mid-cycle",
                "valuation_change": "Sustained premium for quality",
                "market_leadership": "Large private banks led",
                "recovery_time": "Already mid-cycle strength",
            },
            "timeline_refs": ["hsip:banking:FY2022", "india:2022:Inflation Cycle"],
            "research_refs": ["Sector Research: 2022 NIM expansion"],
        },
        {
            "period": "2025",
            "label": "Soft-landing credit — stable ROE / moderate valuation",
            "features": {
                "revenue_growth": 13.0,
                "earnings_growth": 14.0,
                "margin_profile": 3.6,
                "roe": 15.5,
                "valuation": 17.5,
                "relative_performance": 4.0,
                "interest_rate": 6.5,
                "inflation": 3.7,
                "currency": 83.5,
                "policy": 6.5,
                "industry_structure": 7.5,
            },
            "outcome": "Credit growth solid; deposit competition elevated; ROE resilient",
            "equity_outcome": "Constructive but selective; valuation discipline returned",
            "historical_outcome_bundle": {
                "sector_return": "Modest relative outperformance",
                "revenue_growth": "Low-teens loan growth",
                "margin_trend": "NIM normalisation from peaks",
                "valuation_change": "Range-bound multiples",
                "market_leadership": "Private banks remain leaders",
                "recovery_time": "Ongoing mid-cycle",
            },
            "timeline_refs": ["hsip:banking:FY2025", "hsip:banking:timeline"],
            "research_refs": ["Sector Research: 2025 banking soft-landing"],
        },
    ],
    "IT Services": [
        {
            "period": "2008",
            "label": "GFC demand shock — deal deferrals",
            "features": {
                "revenue_growth": 8.0,
                "earnings_growth": 2.0,
                "margin_profile": 26.0,
                "roe": 28.0,
                "valuation": 14.0,
                "relative_performance": -10.0,
                "interest_rate": 9.0,
                "inflation": 8.3,
                "currency": 48.0,
                "policy": 5.0,
                "industry_structure": 7.0,
            },
            "outcome": "Discretionary spend cut; INR depreciation later cushioned exporters",
            "equity_outcome": "Underperformed then recovered with USD strength",
            "historical_outcome_bundle": {
                "sector_return": "Drawdown then exporter rebound",
                "revenue_growth": "Deceleration in discretionary verticals",
                "margin_trend": "Wage pressure managed",
                "valuation_change": "De-rating then re-rating",
                "market_leadership": "TCS / Infosys relative quality",
                "recovery_time": "4-6 quarters",
            },
            "timeline_refs": ["hsip:it_services:FY2008", "india:2008:GFC"],
            "research_refs": ["Sector Research: IT GFC demand shock"],
        },
        {
            "period": "2013",
            "label": "INR stress — exporter FX windfall",
            "features": {
                "revenue_growth": 14.0,
                "earnings_growth": 18.0,
                "margin_profile": 27.0,
                "roe": 30.0,
                "valuation": 16.0,
                "relative_performance": 12.0,
                "interest_rate": 7.75,
                "inflation": 9.5,
                "currency": 68.0,
                "policy": 5.5,
                "industry_structure": 7.5,
            },
            "outcome": "USD/INR spike boosted reported growth and margins",
            "equity_outcome": "IT outperformed domestics during INR stress",
            "historical_outcome_bundle": {
                "sector_return": "Relative outperformance",
                "revenue_growth": "FX-aided constant currency still mid-teens",
                "margin_trend": "FX tailwind",
                "valuation_change": "Modest premium",
                "market_leadership": "Tier-1 IT led",
                "recovery_time": "Immediate FX benefit",
            },
            "timeline_refs": ["hsip:it_services:FY2013", "india:2013:Taper Tantrum"],
            "research_refs": ["Sector Research: 2013 IT FX windfall"],
        },
        {
            "period": "2017",
            "label": "Digital transformation acceleration",
            "features": {
                "revenue_growth": 10.0,
                "earnings_growth": 9.0,
                "margin_profile": 25.0,
                "roe": 26.0,
                "valuation": 18.0,
                "relative_performance": 2.0,
                "interest_rate": 6.0,
                "inflation": 3.3,
                "currency": 65.0,
                "policy": 6.0,
                "industry_structure": 7.5,
            },
            "outcome": "Digital moves from pilots to programmes; attrition elevated",
            "equity_outcome": "Selective winners; valuation gap vs traditional IT",
            "historical_outcome_bundle": {
                "sector_return": "In-line to modest outperformance",
                "revenue_growth": "High-single to low-double digit",
                "margin_trend": "Wage inflation pressure",
                "valuation_change": "Digital premium emerging",
                "market_leadership": "Digital-heavy franchises led",
                "recovery_time": "Multi-year digital cycle",
            },
            "timeline_refs": ["hsip:it_services:FY2017", "hsip:it_services:timeline"],
            "research_refs": ["Sector Research: Digital IT 2017"],
        },
        {
            "period": "2020",
            "label": "COVID digital acceleration",
            "features": {
                "revenue_growth": 4.0,
                "earnings_growth": 6.0,
                "margin_profile": 25.5,
                "roe": 27.0,
                "valuation": 24.0,
                "relative_performance": 15.0,
                "interest_rate": 4.0,
                "inflation": 6.2,
                "currency": 76.0,
                "policy": 7.0,
                "industry_structure": 8.0,
            },
            "outcome": "Near-term deal pause then cloud / digital surge",
            "equity_outcome": "Strong relative rally into 2021",
            "historical_outcome_bundle": {
                "sector_return": "Outperformed into 2021",
                "revenue_growth": "Re-accelerated post pause",
                "margin_trend": "Cost control then hiring wave",
                "valuation_change": "Peak multiples",
                "market_leadership": "Tier-1 + digital specialists",
                "recovery_time": "2-3 quarters",
            },
            "timeline_refs": ["hsip:it_services:FY2020", "india:2020:COVID Policy Response"],
            "research_refs": ["Sector Research: COVID digital IT"],
        },
        {
            "period": "2022",
            "label": "Post-pandemic demand air-pocket",
            "features": {
                "revenue_growth": 8.0,
                "earnings_growth": 5.0,
                "margin_profile": 23.0,
                "roe": 24.0,
                "valuation": 22.0,
                "relative_performance": -14.0,
                "interest_rate": 6.25,
                "inflation": 6.7,
                "currency": 82.0,
                "policy": 5.5,
                "industry_structure": 7.5,
            },
            "outcome": "Client budget caution; deal TCV softer; attrition cooled",
            "equity_outcome": "De-rating vs 2021 peaks; underperformed financials",
            "historical_outcome_bundle": {
                "sector_return": "Underperformed domestics",
                "revenue_growth": "Deceleration into high-single digit",
                "margin_trend": "Wage cost lag",
                "valuation_change": "Multiple compression",
                "market_leadership": "Quality franchises defended",
                "recovery_time": "4-8 quarters for demand reset",
            },
            "timeline_refs": ["hsip:it_services:FY2022", "hsip:it_services:timeline"],
            "research_refs": ["Sector Research: 2022 IT demand air-pocket"],
        },
        {
            "period": "2025",
            "label": "AI-led selective recovery",
            "features": {
                "revenue_growth": 7.0,
                "earnings_growth": 8.0,
                "margin_profile": 24.0,
                "roe": 25.0,
                "valuation": 26.0,
                "relative_performance": 3.0,
                "interest_rate": 6.5,
                "inflation": 3.7,
                "currency": 83.5,
                "policy": 6.0,
                "industry_structure": 8.0,
            },
            "outcome": "GenAI deals emerge; traditional discretionary still cautious",
            "equity_outcome": "Selective re-rating; leadership by AI-capable Tier-1",
            "historical_outcome_bundle": {
                "sector_return": "Modest relative recovery",
                "revenue_growth": "High-single digit",
                "margin_trend": "Stabilising",
                "valuation_change": "AI premium emerging",
                "market_leadership": "Infosys / TCS / HCLTech",
                "recovery_time": "Ongoing",
            },
            "timeline_refs": ["hsip:it_services:FY2025", "hsip:it_services:timeline"],
            "research_refs": ["Sector Research: 2025 AI IT cycle"],
        },
    ],
    "FMCG": [
        {
            "period": "2008",
            "label": "GFC — defensive staples demand",
            "features": {
                "revenue_growth": 14.0,
                "earnings_growth": 12.0,
                "margin_profile": 18.0,
                "roe": 28.0,
                "valuation": 28.0,
                "relative_performance": 8.0,
                "interest_rate": 9.0,
                "inflation": 8.3,
                "currency": 48.0,
                "policy": 5.0,
                "industry_structure": 8.0,
            },
            "outcome": "Volume resilient; pricing power defended margins",
            "equity_outcome": "Defensive outperformance",
            "historical_outcome_bundle": {
                "sector_return": "Relative outperformance",
                "revenue_growth": "Resilient mid-teens",
                "margin_trend": "Stable",
                "valuation_change": "Premium held",
                "market_leadership": "HUL / ITC",
                "recovery_time": "Immediate defensive bid",
            },
            "timeline_refs": ["hsip:fmcg:FY2008"],
            "research_refs": ["Sector Research: FMCG GFC defensive"],
        },
        {
            "period": "2013",
            "label": "High CPI — rural stress",
            "features": {
                "revenue_growth": 11.0,
                "earnings_growth": 8.0,
                "margin_profile": 17.0,
                "roe": 26.0,
                "valuation": 32.0,
                "relative_performance": -2.0,
                "interest_rate": 7.75,
                "inflation": 9.5,
                "currency": 68.0,
                "policy": 5.0,
                "industry_structure": 8.0,
            },
            "outcome": "Rural demand soft; urban held; input cost volatility",
            "equity_outcome": "Mixed; premium valuations compressed slightly",
            "historical_outcome_bundle": {
                "sector_return": "In-line to slight underperformance",
                "revenue_growth": "Volume pressure in rural",
                "margin_trend": "Input cost swings",
                "valuation_change": "Modest compression",
                "market_leadership": "Urban-skewed brands better",
                "recovery_time": "With CPI cool-down",
            },
            "timeline_refs": ["hsip:fmcg:FY2013"],
            "research_refs": ["Sector Research: 2013 FMCG rural stress"],
        },
        {
            "period": "2017",
            "label": "GST transition + rural recovery",
            "features": {
                "revenue_growth": 9.0,
                "earnings_growth": 10.0,
                "margin_profile": 19.0,
                "roe": 27.0,
                "valuation": 42.0,
                "relative_performance": 5.0,
                "interest_rate": 6.0,
                "inflation": 3.3,
                "currency": 65.0,
                "policy": 7.0,
                "industry_structure": 8.0,
            },
            "outcome": "GST disruption then formalisation benefit; rural rebounded",
            "equity_outcome": "Premium re-rating for organised leaders",
            "historical_outcome_bundle": {
                "sector_return": "Constructive",
                "revenue_growth": "Normalised post GST",
                "margin_trend": "Improving mix",
                "valuation_change": "Peak premium",
                "market_leadership": "HUL / Nestle / Britannia",
                "recovery_time": "2-3 quarters post GST",
            },
            "timeline_refs": ["hsip:fmcg:FY2017"],
            "research_refs": ["Sector Research: GST FMCG"],
        },
        {
            "period": "2020",
            "label": "COVID staples surge then normalisation",
            "features": {
                "revenue_growth": 8.0,
                "earnings_growth": 9.0,
                "margin_profile": 20.0,
                "roe": 28.0,
                "valuation": 48.0,
                "relative_performance": 10.0,
                "interest_rate": 4.0,
                "inflation": 6.2,
                "currency": 76.0,
                "policy": 7.5,
                "industry_structure": 8.0,
            },
            "outcome": "At-home consumption spike; discretionary FMCG lagged staples",
            "equity_outcome": "Initial outperformance then mean-reversion",
            "historical_outcome_bundle": {
                "sector_return": "Defensive rally then digest",
                "revenue_growth": "Staples surge",
                "margin_trend": "A&P reallocation",
                "valuation_change": "Peak multiples",
                "market_leadership": "Staples leaders",
                "recovery_time": "Normalisation into 2021",
            },
            "timeline_refs": ["hsip:fmcg:FY2020"],
            "research_refs": ["Sector Research: COVID FMCG"],
        },
        {
            "period": "2022",
            "label": "Input cost inflation — pricing vs volume",
            "features": {
                "revenue_growth": 12.0,
                "earnings_growth": 6.0,
                "margin_profile": 17.5,
                "roe": 24.0,
                "valuation": 45.0,
                "relative_performance": -4.0,
                "interest_rate": 6.25,
                "inflation": 6.7,
                "currency": 82.0,
                "policy": 5.5,
                "industry_structure": 8.0,
            },
            "outcome": "Aggressive pricing; rural volume weak; margins compressed then repaired",
            "equity_outcome": "Underperformed until commodity cool-down",
            "historical_outcome_bundle": {
                "sector_return": "Lagged until 2023",
                "revenue_growth": "Value growth over volume",
                "margin_trend": "Compressed then recovered",
                "valuation_change": "Premium defended selectively",
                "market_leadership": "Pricing-power brands",
                "recovery_time": "3-5 quarters",
            },
            "timeline_refs": ["hsip:fmcg:FY2022"],
            "research_refs": ["Sector Research: 2022 FMCG input inflation"],
        },
        {
            "period": "2025",
            "label": "Volume recovery — margin repair",
            "features": {
                "revenue_growth": 8.0,
                "earnings_growth": 11.0,
                "margin_profile": 19.5,
                "roe": 26.0,
                "valuation": 50.0,
                "relative_performance": 2.0,
                "interest_rate": 6.5,
                "inflation": 3.7,
                "currency": 83.5,
                "policy": 6.0,
                "industry_structure": 8.0,
            },
            "outcome": "Rural volume improving; gross margins repairing",
            "equity_outcome": "Constructive with premium valuations",
            "historical_outcome_bundle": {
                "sector_return": "Modest outperformance",
                "revenue_growth": "Volume-led mid/high single digit",
                "margin_trend": "Repairing",
                "valuation_change": "Premium sustained",
                "market_leadership": "Category leaders",
                "recovery_time": "Ongoing",
            },
            "timeline_refs": ["hsip:fmcg:FY2025"],
            "research_refs": ["Sector Research: 2025 FMCG volume recovery"],
        },
    ],
    "Auto": [
        {
            "period": "2008",
            "label": "GFC demand collapse",
            "features": {
                "revenue_growth": -5.0,
                "earnings_growth": -25.0,
                "margin_profile": 10.0,
                "roe": 12.0,
                "valuation": 12.0,
                "relative_performance": -22.0,
                "interest_rate": 9.0,
                "inflation": 8.3,
                "currency": 48.0,
                "policy": 4.0,
                "industry_structure": 6.0,
            },
            "outcome": "Financing dried up; volumes collapsed; inventory destock",
            "equity_outcome": "Deep underperformance; multi-year recovery",
            "historical_outcome_bundle": {
                "sector_return": "Severe underperformance",
                "revenue_growth": "Negative",
                "margin_trend": "Operating leverage pain",
                "valuation_change": "De-rating",
                "market_leadership": "Cash-rich OEMs survived better",
                "recovery_time": "2-3 years",
            },
            "timeline_refs": ["hsip:auto:FY2008"],
            "research_refs": ["Sector Research: Auto GFC"],
        },
        {
            "period": "2013",
            "label": "High rates + diesel regulation stress",
            "features": {
                "revenue_growth": 2.0,
                "earnings_growth": -5.0,
                "margin_profile": 11.0,
                "roe": 14.0,
                "valuation": 16.0,
                "relative_performance": -6.0,
                "interest_rate": 7.75,
                "inflation": 9.5,
                "currency": 68.0,
                "policy": 4.5,
                "industry_structure": 6.5,
            },
            "outcome": "PV soft; 2W rural weak; financing costly",
            "equity_outcome": "Selective underperformance",
            "historical_outcome_bundle": {
                "sector_return": "Lagged market",
                "revenue_growth": "Near flat",
                "margin_trend": "Pressure",
                "valuation_change": "Compressed",
                "market_leadership": "Maruti relative resilience",
                "recovery_time": "With rate easing",
            },
            "timeline_refs": ["hsip:auto:FY2013"],
            "research_refs": ["Sector Research: 2013 Auto soft patch"],
        },
        {
            "period": "2017",
            "label": "PV upcycle + financing availability",
            "features": {
                "revenue_growth": 12.0,
                "earnings_growth": 18.0,
                "margin_profile": 13.0,
                "roe": 18.0,
                "valuation": 24.0,
                "relative_performance": 8.0,
                "interest_rate": 6.0,
                "inflation": 3.3,
                "currency": 65.0,
                "policy": 6.5,
                "industry_structure": 7.0,
            },
            "outcome": "Strong PV demand; NBFC financing supportive",
            "equity_outcome": "OEM outperformance",
            "historical_outcome_bundle": {
                "sector_return": "Outperformed",
                "revenue_growth": "Double-digit",
                "margin_trend": "Operating leverage",
                "valuation_change": "Re-rating",
                "market_leadership": "Maruti / M&M",
                "recovery_time": "Mid-cycle",
            },
            "timeline_refs": ["hsip:auto:FY2017"],
            "research_refs": ["Sector Research: 2017 Auto upcycle"],
        },
        {
            "period": "2020",
            "label": "COVID shutdown then pent-up demand",
            "features": {
                "revenue_growth": -15.0,
                "earnings_growth": -40.0,
                "margin_profile": 9.0,
                "roe": 8.0,
                "valuation": 28.0,
                "relative_performance": -8.0,
                "interest_rate": 4.0,
                "inflation": 6.2,
                "currency": 76.0,
                "policy": 8.0,
                "industry_structure": 6.5,
            },
            "outcome": "Factory shutdown; then personal mobility preference rebound",
            "equity_outcome": "Crash then sharp recovery into 2021",
            "historical_outcome_bundle": {
                "sector_return": "V-shaped",
                "revenue_growth": "Collapse then surge",
                "margin_trend": "Fixed cost pain then leverage",
                "valuation_change": "Volatile",
                "market_leadership": "PV leaders",
                "recovery_time": "2-4 quarters",
            },
            "timeline_refs": ["hsip:auto:FY2020"],
            "research_refs": ["Sector Research: COVID Auto"],
        },
        {
            "period": "2022",
            "label": "Semiconductor / commodity cost cycle",
            "features": {
                "revenue_growth": 18.0,
                "earnings_growth": 25.0,
                "margin_profile": 12.5,
                "roe": 16.0,
                "valuation": 26.0,
                "relative_performance": 6.0,
                "interest_rate": 6.25,
                "inflation": 6.7,
                "currency": 82.0,
                "policy": 6.0,
                "industry_structure": 7.0,
            },
            "outcome": "Supply constraints limited volumes; pricing supported margins",
            "equity_outcome": "Strong absolute returns despite costs",
            "historical_outcome_bundle": {
                "sector_return": "Outperformed",
                "revenue_growth": "Price + mix led",
                "margin_trend": "Commodity pressure managed",
                "valuation_change": "Sustained",
                "market_leadership": "UV-focused OEMs",
                "recovery_time": "Supply easing into 2023",
            },
            "timeline_refs": ["hsip:auto:FY2022"],
            "research_refs": ["Sector Research: 2022 Auto supply cycle"],
        },
        {
            "period": "2025",
            "label": "Steady demand — EV transition overlay",
            "features": {
                "revenue_growth": 10.0,
                "earnings_growth": 12.0,
                "margin_profile": 13.5,
                "roe": 17.0,
                "valuation": 28.0,
                "relative_performance": 3.0,
                "interest_rate": 6.5,
                "inflation": 3.7,
                "currency": 83.5,
                "policy": 7.0,
                "industry_structure": 7.0,
            },
            "outcome": "PV steady; EV share rising; financing still supportive",
            "equity_outcome": "Constructive with EV narrative premium",
            "historical_outcome_bundle": {
                "sector_return": "Modest outperformance",
                "revenue_growth": "High-single / low-double",
                "margin_trend": "Stable",
                "valuation_change": "EV premium selective",
                "market_leadership": "Maruti / M&M / EV leaders",
                "recovery_time": "Ongoing cycle",
            },
            "timeline_refs": ["hsip:auto:FY2025"],
            "research_refs": ["Sector Research: 2025 Auto EV overlay"],
        },
    ],
    "Capital Goods": [
        {
            "period": "2008",
            "label": "GFC capex freeze",
            "features": {
                "revenue_growth": -8.0,
                "earnings_growth": -30.0,
                "margin_profile": 10.0,
                "roe": 10.0,
                "valuation": 14.0,
                "relative_performance": -20.0,
                "interest_rate": 9.0,
                "inflation": 8.3,
                "currency": 48.0,
                "policy": 3.0,
                "industry_structure": 5.5,
            },
            "outcome": "Order books collapsed; private capex froze",
            "equity_outcome": "Deep underperformance",
            "historical_outcome_bundle": {
                "sector_return": "Severe drawdown",
                "revenue_growth": "Negative",
                "margin_trend": "Operating leverage pain",
                "valuation_change": "De-rating",
                "market_leadership": "Balance-sheet strength mattered",
                "recovery_time": "Multi-year",
            },
            "timeline_refs": ["hsip:capital_goods:FY2008"],
            "research_refs": ["Sector Research: Cap Goods GFC"],
        },
        {
            "period": "2013",
            "label": "Policy uncertainty — stalled projects",
            "features": {
                "revenue_growth": 3.0,
                "earnings_growth": -2.0,
                "margin_profile": 11.0,
                "roe": 11.0,
                "valuation": 18.0,
                "relative_performance": -5.0,
                "interest_rate": 7.75,
                "inflation": 9.5,
                "currency": 68.0,
                "policy": 4.0,
                "industry_structure": 6.0,
            },
            "outcome": "Clearance delays; weak private investment",
            "equity_outcome": "Laggard vs consumption",
            "historical_outcome_bundle": {
                "sector_return": "Underperformed",
                "revenue_growth": "Low single digit",
                "margin_trend": "Soft",
                "valuation_change": "Compressed",
                "market_leadership": "L&T relative quality",
                "recovery_time": "Policy reform dependent",
            },
            "timeline_refs": ["hsip:capital_goods:FY2013"],
            "research_refs": ["Sector Research: 2013 Cap Goods stall"],
        },
        {
            "period": "2017",
            "label": "Early infra push — order book rebuild",
            "features": {
                "revenue_growth": 10.0,
                "earnings_growth": 14.0,
                "margin_profile": 12.0,
                "roe": 14.0,
                "valuation": 28.0,
                "relative_performance": 7.0,
                "interest_rate": 6.0,
                "inflation": 3.3,
                "currency": 65.0,
                "policy": 7.5,
                "industry_structure": 6.5,
            },
            "outcome": "Government capex revived; order inflows improved",
            "equity_outcome": "Re-rating on order book visibility",
            "historical_outcome_bundle": {
                "sector_return": "Outperformed",
                "revenue_growth": "Double-digit emerging",
                "margin_trend": "Improving",
                "valuation_change": "Re-rating",
                "market_leadership": "L&T / Siemens",
                "recovery_time": "Multi-year capex cycle start",
            },
            "timeline_refs": ["hsip:capital_goods:FY2017"],
            "research_refs": ["Sector Research: 2017 Cap Goods orders"],
        },
        {
            "period": "2020",
            "label": "COVID project delays",
            "features": {
                "revenue_growth": -10.0,
                "earnings_growth": -20.0,
                "margin_profile": 10.5,
                "roe": 9.0,
                "valuation": 22.0,
                "relative_performance": -6.0,
                "interest_rate": 4.0,
                "inflation": 6.2,
                "currency": 76.0,
                "policy": 8.0,
                "industry_structure": 6.0,
            },
            "outcome": "Site shutdowns; then government capex backstop",
            "equity_outcome": "Volatile; infra theme returned late 2020",
            "historical_outcome_bundle": {
                "sector_return": "Drawdown then recovery",
                "revenue_growth": "Paused",
                "margin_trend": "Soft",
                "valuation_change": "Volatile",
                "market_leadership": "Order-book leaders",
                "recovery_time": "2-4 quarters",
            },
            "timeline_refs": ["hsip:capital_goods:FY2020"],
            "research_refs": ["Sector Research: COVID Cap Goods"],
        },
        {
            "period": "2022",
            "label": "Government capex supercycle",
            "features": {
                "revenue_growth": 16.0,
                "earnings_growth": 22.0,
                "margin_profile": 13.0,
                "roe": 16.0,
                "valuation": 32.0,
                "relative_performance": 14.0,
                "interest_rate": 6.25,
                "inflation": 6.7,
                "currency": 82.0,
                "policy": 9.0,
                "industry_structure": 7.0,
            },
            "outcome": "Strong order books; railways / roads / power equipment",
            "equity_outcome": "Sustained outperformance",
            "historical_outcome_bundle": {
                "sector_return": "Strong outperformance",
                "revenue_growth": "Mid-teens+",
                "margin_trend": "Operating leverage",
                "valuation_change": "Premium expansion",
                "market_leadership": "L&T / ABB / Siemens",
                "recovery_time": "Mid-cycle strength",
            },
            "timeline_refs": ["hsip:capital_goods:FY2022"],
            "research_refs": ["Sector Research: 2022 Capex supercycle"],
        },
        {
            "period": "2025",
            "label": "Sustained infra + manufacturing PLI",
            "features": {
                "revenue_growth": 14.0,
                "earnings_growth": 16.0,
                "margin_profile": 13.5,
                "roe": 17.0,
                "valuation": 36.0,
                "relative_performance": 8.0,
                "interest_rate": 6.5,
                "inflation": 3.7,
                "currency": 83.5,
                "policy": 8.5,
                "industry_structure": 7.0,
            },
            "outcome": "Order books elevated; execution focus; private capex nascent",
            "equity_outcome": "Still constructive; valuation discipline rising",
            "historical_outcome_bundle": {
                "sector_return": "Outperformance moderating",
                "revenue_growth": "Low-to-mid teens",
                "margin_trend": "Stable-to-up",
                "valuation_change": "Premium high",
                "market_leadership": "Order-book compounders",
                "recovery_time": "Ongoing cycle",
            },
            "timeline_refs": ["hsip:capital_goods:FY2025"],
            "research_refs": ["Sector Research: 2025 Cap Goods PLI"],
        },
    ],
    "Pharma": [
        {
            "period": "2008",
            "label": "GFC — defensive healthcare demand",
            "features": {
                "revenue_growth": 12.0,
                "earnings_growth": 10.0,
                "margin_profile": 22.0,
                "roe": 18.0,
                "valuation": 18.0,
                "relative_performance": 5.0,
                "interest_rate": 9.0,
                "inflation": 8.3,
                "currency": 48.0,
                "policy": 5.0,
                "industry_structure": 6.5,
            },
            "outcome": "Domestic formulations resilient; US generics mixed",
            "equity_outcome": "Defensive relative bid",
            "historical_outcome_bundle": {
                "sector_return": "Relative outperformance",
                "revenue_growth": "Steady",
                "margin_trend": "Stable",
                "valuation_change": "Defended",
                "market_leadership": "Diversified franchises",
                "recovery_time": "Immediate defensive",
            },
            "timeline_refs": ["hsip:pharma:FY2008"],
            "research_refs": ["Sector Research: Pharma GFC"],
        },
        {
            "period": "2013",
            "label": "USFDA scrutiny wave",
            "features": {
                "revenue_growth": 10.0,
                "earnings_growth": 4.0,
                "margin_profile": 20.0,
                "roe": 15.0,
                "valuation": 20.0,
                "relative_performance": -4.0,
                "interest_rate": 7.75,
                "inflation": 9.5,
                "currency": 68.0,
                "policy": 4.0,
                "industry_structure": 6.0,
            },
            "outcome": "Plant observations hit select names; INR helped exporters",
            "equity_outcome": "Stock-specific divergence",
            "historical_outcome_bundle": {
                "sector_return": "Mixed",
                "revenue_growth": "Uneven",
                "margin_trend": "Remediation costs",
                "valuation_change": "Quality premium",
                "market_leadership": "Compliance leaders",
                "recovery_time": "Company-specific",
            },
            "timeline_refs": ["hsip:pharma:FY2013"],
            "research_refs": ["Sector Research: 2013 USFDA wave"],
        },
        {
            "period": "2017",
            "label": "US pricing pressure trough",
            "features": {
                "revenue_growth": 6.0,
                "earnings_growth": -2.0,
                "margin_profile": 18.0,
                "roe": 12.0,
                "valuation": 22.0,
                "relative_performance": -8.0,
                "interest_rate": 6.0,
                "inflation": 3.3,
                "currency": 65.0,
                "policy": 5.0,
                "industry_structure": 6.0,
            },
            "outcome": "US base business eroded; India / EM growth offset",
            "equity_outcome": "Prolonged underperformance for pure US plays",
            "historical_outcome_bundle": {
                "sector_return": "Underperformed",
                "revenue_growth": "Muted",
                "margin_trend": "Compressed",
                "valuation_change": "De-rating",
                "market_leadership": "India-centric names better",
                "recovery_time": "Multi-year",
            },
            "timeline_refs": ["hsip:pharma:FY2017"],
            "research_refs": ["Sector Research: US pricing trough"],
        },
        {
            "period": "2020",
            "label": "COVID therapeutics / API spotlight",
            "features": {
                "revenue_growth": 14.0,
                "earnings_growth": 16.0,
                "margin_profile": 21.0,
                "roe": 16.0,
                "valuation": 28.0,
                "relative_performance": 12.0,
                "interest_rate": 4.0,
                "inflation": 6.2,
                "currency": 76.0,
                "policy": 8.0,
                "industry_structure": 6.5,
            },
            "outcome": "API / hospital demand spike; later normalisation",
            "equity_outcome": "COVID winners then mean-reversion",
            "historical_outcome_bundle": {
                "sector_return": "Outperformed then digested",
                "revenue_growth": "Spike",
                "margin_trend": "Temporary lift",
                "valuation_change": "COVID premium",
                "market_leadership": "API / specialty",
                "recovery_time": "Normalisation 2021-22",
            },
            "timeline_refs": ["hsip:pharma:FY2020"],
            "research_refs": ["Sector Research: COVID Pharma"],
        },
        {
            "period": "2022",
            "label": "Post-COVID digestion + US recovery seeds",
            "features": {
                "revenue_growth": 7.0,
                "earnings_growth": 5.0,
                "margin_profile": 19.0,
                "roe": 13.0,
                "valuation": 24.0,
                "relative_performance": -3.0,
                "interest_rate": 6.25,
                "inflation": 6.7,
                "currency": 82.0,
                "policy": 6.0,
                "industry_structure": 6.5,
            },
            "outcome": "COVID base faded; US price erosion slowed for some",
            "equity_outcome": "Selective recovery starting",
            "historical_outcome_bundle": {
                "sector_return": "Lagged then selective",
                "revenue_growth": "Normalising",
                "margin_trend": "Stabilising",
                "valuation_change": "Reasonable",
                "market_leadership": "Complex generics / India",
                "recovery_time": "Ongoing",
            },
            "timeline_refs": ["hsip:pharma:FY2022"],
            "research_refs": ["Sector Research: 2022 Pharma digestion"],
        },
        {
            "period": "2025",
            "label": "US recovery + India chronic growth",
            "features": {
                "revenue_growth": 10.0,
                "earnings_growth": 12.0,
                "margin_profile": 20.5,
                "roe": 15.0,
                "valuation": 30.0,
                "relative_performance": 4.0,
                "interest_rate": 6.5,
                "inflation": 3.7,
                "currency": 83.5,
                "policy": 6.5,
                "industry_structure": 6.5,
            },
            "outcome": "US price erosion easing; chronic therapies grow domestically",
            "equity_outcome": "Constructive selective re-rating",
            "historical_outcome_bundle": {
                "sector_return": "Modest outperformance",
                "revenue_growth": "High-single / low-double",
                "margin_trend": "Improving",
                "valuation_change": "Re-rating quality names",
                "market_leadership": "Diversified exporters",
                "recovery_time": "Ongoing",
            },
            "timeline_refs": ["hsip:pharma:FY2025"],
            "research_refs": ["Sector Research: 2025 Pharma recovery"],
        },
    ],
}

# Current-period tip vectors (closest to 2025 soft-landing / selective recovery).
CURRENT_REGIME_TIPS: dict[str, dict[str, Any]] = {
    "Banking": {
        "period": "2026",
        "label": "Current — stable credit, NIM normalisation",
        "features": {
            "revenue_growth": 12.5,
            "earnings_growth": 13.0,
            "margin_profile": 3.55,
            "roe": 15.2,
            "valuation": 17.0,
            "relative_performance": 3.0,
            "interest_rate": 6.25,
            "inflation": 3.9,
            "currency": 84.0,
            "policy": 6.5,
            "industry_structure": 7.5,
        },
    },
    "IT Services": {
        "period": "2026",
        "label": "Current — AI selective recovery, cautious discretionary",
        "features": {
            "revenue_growth": 6.5,
            "earnings_growth": 7.5,
            "margin_profile": 23.8,
            "roe": 24.5,
            "valuation": 25.0,
            "relative_performance": 2.0,
            "interest_rate": 6.25,
            "inflation": 3.9,
            "currency": 84.0,
            "policy": 6.0,
            "industry_structure": 8.0,
        },
    },
    "FMCG": {
        "period": "2026",
        "label": "Current — rural volume recovery, margin repair",
        "features": {
            "revenue_growth": 7.5,
            "earnings_growth": 10.5,
            "margin_profile": 19.2,
            "roe": 25.5,
            "valuation": 49.0,
            "relative_performance": 1.5,
            "interest_rate": 6.25,
            "inflation": 3.9,
            "currency": 84.0,
            "policy": 6.0,
            "industry_structure": 8.0,
        },
    },
    "Auto": {
        "period": "2026",
        "label": "Current — steady PV, EV transition",
        "features": {
            "revenue_growth": 9.5,
            "earnings_growth": 11.0,
            "margin_profile": 13.2,
            "roe": 16.5,
            "valuation": 27.0,
            "relative_performance": 2.5,
            "interest_rate": 6.25,
            "inflation": 3.9,
            "currency": 84.0,
            "policy": 7.0,
            "industry_structure": 7.0,
        },
    },
    "Capital Goods": {
        "period": "2026",
        "label": "Current — elevated order books, infra execution",
        "features": {
            "revenue_growth": 13.5,
            "earnings_growth": 15.0,
            "margin_profile": 13.2,
            "roe": 16.5,
            "valuation": 35.0,
            "relative_performance": 7.0,
            "interest_rate": 6.25,
            "inflation": 3.9,
            "currency": 84.0,
            "policy": 8.5,
            "industry_structure": 7.0,
        },
    },
    "Pharma": {
        "period": "2026",
        "label": "Current — US recovery seeds, India chronic",
        "features": {
            "revenue_growth": 9.5,
            "earnings_growth": 11.5,
            "margin_profile": 20.0,
            "roe": 14.5,
            "valuation": 29.0,
            "relative_performance": 3.5,
            "interest_rate": 6.25,
            "inflation": 3.9,
            "currency": 84.0,
            "policy": 6.5,
            "industry_structure": 6.5,
        },
    },
}


def normalize_sector(name: str | None) -> str | None:
    if not name:
        return None
    raw = str(name).strip()
    for s in SUPPORTED_SECTORS:
        if raw.lower() == s.lower():
            return s
    aliases = {
        "banks": "Banking",
        "banking": "Banking",
        "financials": "Banking",
        "it": "IT Services",
        "it_services": "IT Services",
        "information_technology": "IT Services",
        "fmcg": "FMCG",
        "auto": "Auto",
        "automobiles": "Auto",
        "capital_goods": "Capital Goods",
        "capital goods": "Capital Goods",
        "pharma": "Pharma",
        "pharmaceuticals": "Pharma",
    }
    key = raw.lower().replace("-", "_").replace(" ", "_")
    if key in aliases:
        return aliases[key]
    try:
        from continuous_sector_knowledge.schema import canonicalize

        ck = canonicalize(raw)
        inv = {v: k for k, v in SECTOR_KEY_MAP.items()}
        if ck in inv:
            return inv[ck]
    except Exception:
        pass
    return None


def catalog_regimes(*, sector: str) -> list[SectorRegime]:
    sector_n = normalize_sector(sector) or sector
    rows = SECTOR_REGIME_CATALOG.get(sector_n) or []
    out: list[SectorRegime] = []
    for row in rows:
        out.append(
            SectorRegime(
                sector=sector_n,
                sector_key=SECTOR_KEY_MAP.get(sector_n),
                period=str(row["period"]),
                label=str(row["label"]),
                features=dict(row["features"]),
                feature_units=dict(FEATURE_UNITS),
                outcome=row.get("outcome"),
                equity_outcome=row.get("equity_outcome"),
                historical_outcome_bundle=dict(row.get("historical_outcome_bundle") or {}),
                timeline_refs=list(row.get("timeline_refs") or []),
                research_refs=list(row.get("research_refs") or []),
                source_layers=["hsai_regime_catalog"],
                provenance={
                    "kind": "institutional_catalog",
                    "aligned_with": "HSIP_seeded_series",
                },
            )
        )
    return out


def build_historical_regimes(
    *,
    sector: str,
    enrich_hsip: bool = True,
) -> list[SectorRegime]:
    regimes = catalog_regimes(sector=sector)
    if enrich_hsip:
        regimes = [enrich_regime_from_hsip(r) for r in regimes]
    return regimes


def build_current_regime(*, sector: str, enrich_cskp: bool = True) -> SectorRegime:
    sector_n = normalize_sector(sector) or sector
    tip = CURRENT_REGIME_TIPS.get(sector_n) or CURRENT_REGIME_TIPS["Banking"]
    features = dict(tip["features"])
    layers = ["hsai_current_tip"]
    provenance: dict[str, Any] = {"kind": "current_tip"}

    if enrich_cskp:
        overlay = soft_cskp_current_features(sector_n)
        if overlay:
            features = {**features, **overlay}
            layers.append("CSKP")
            provenance["cskp_overlay_keys"] = sorted(overlay.keys())

    # Soft macro tip from HMIP for rate / inflation / FX when available
    macro = soft_hmip_macro_features()
    if macro:
        for k, v in macro.items():
            if v is not None:
                features[k] = v
        layers.append("HMIP")
        provenance["hmip_overlay_keys"] = sorted(macro.keys())

    return SectorRegime(
        sector=sector_n,
        sector_key=SECTOR_KEY_MAP.get(sector_n),
        period=str(tip["period"]),
        label=str(tip["label"]),
        features=features,
        feature_units=dict(FEATURE_UNITS),
        outcome="Current observation window — outcomes deferred to Forecast Intelligence",
        equity_outcome=None,
        timeline_refs=[f"cskp:{SECTOR_KEY_MAP.get(sector_n, sector_n)}:latest"],
        research_refs=[f"Sector Research: current {sector_n}"],
        source_layers=layers,
        provenance=provenance,
    )


def soft_cskp_current_features(sector: str) -> dict[str, float]:
    """Map published CSKP tips into dimension features — never collects."""
    try:
        from continuous_sector_knowledge.production import sector as cskp_sector
        from continuous_sector_knowledge.schema import canonicalize
    except Exception:
        return {}

    key = SECTOR_KEY_MAP.get(sector) or canonicalize(sector)
    if not key:
        return {}
    try:
        pack = cskp_sector(key)
    except Exception:
        return {}
    latest = pack.get("latest") or {}
    if not latest:
        return {}

    out: dict[str, float] = {}
    # Outlook-ish ordinals → soft nudges (deterministic mapping)
    outlook = str(latest.get("current_outlook") or latest.get("outlook") or "").lower()
    if "bull" in outlook or "positive" in outlook or "constructive" in outlook:
        out["relative_performance"] = 5.0
        out["revenue_growth"] = float(
            (CURRENT_REGIME_TIPS.get(sector) or {}).get("features", {}).get("revenue_growth", 10) + 1
        )
    elif "bear" in outlook or "negative" in outlook or "cautious" in outlook:
        out["relative_performance"] = -2.0
    return out


def enrich_regime_from_hsip(regime: SectorRegime) -> SectorRegime:
    """Soft-confirm via HSIP timeline completeness — never collects."""
    try:
        from historical_sector_intelligence.production import sector as hsip_sector
    except Exception:
        return regime

    key = regime.sector_key or SECTOR_KEY_MAP.get(regime.sector)
    if not key:
        return regime
    try:
        tip = hsip_sector(key, limit=20)
    except Exception:
        return regime
    if not tip.get("found"):
        return regime

    tl = tip.get("timeline") or {}
    refs = list(regime.timeline_refs)
    refs.append(f"hsip:{key}:timeline")
    layers = list(regime.source_layers or [])
    if "HSIP" not in layers:
        layers.append("HSIP")
    regime.timeline_refs = refs
    regime.source_layers = layers
    regime.provenance = {
        **(regime.provenance or {}),
        "hsip_soft_confirmed": True,
        "hsip_completeness_pct": tl.get("completeness_pct"),
        "providers_queried": [],
    }
    return regime


def soft_hmip_macro_features() -> dict[str, float]:
    """Soft macro overlays for interest / inflation / FX — never collects."""
    out: dict[str, float] = {}
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator
    except Exception:
        return out

    mapping = {
        "Repo Rate": "interest_rate",
        "CPI": "inflation",
        "USDINR": "currency",
    }
    for ind, dim in mapping.items():
        try:
            tip = hmip_indicator(ind, country="India")
        except Exception:
            continue
        if not tip.get("found"):
            continue
        # Prefer latest observation value if present
        obs = tip.get("observations") or tip.get("latest") or []
        val = None
        if isinstance(obs, dict):
            val = obs.get("value")
        elif isinstance(obs, list) and obs:
            val = (obs[-1] or {}).get("value")
        timeline = tip.get("timeline") or {}
        if val is None and timeline.get("latest_value") is not None:
            val = timeline.get("latest_value")
        try:
            if val is not None:
                out[dim] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def soft_sri_relationships(sector: str) -> list[dict[str, Any]]:
    """Soft tip from SRI for explainability — never rebuilds graph."""
    try:
        from sector_relationship_intelligence.production import for_sector
    except Exception:
        return []
    try:
        pack = for_sector(sector, limit=10)
    except Exception:
        return []
    rows = []
    for r in pack.get("relationships") or []:
        rows.append(
            {
                "source": r.get("source"),
                "target": r.get("target"),
                "relationship": r.get("relationship"),
                "direction": r.get("direction"),
                "confidence_pct": r.get("confidence_pct"),
                "kind": r.get("kind"),
                "average_lag": r.get("average_lag"),
                "gateway": "SRI_KRIG",
            }
        )
    return rows


def supported_sectors() -> list[str]:
    return list(SUPPORTED_SECTORS)
