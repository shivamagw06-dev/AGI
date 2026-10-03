"""Map objective → preferred data APIs (plan only)."""

from __future__ import annotations

from typing import Any

_MAP: dict[str, list[str]] = {
    "Investment Evaluation": ["Groww", "IndianAPI", "Yahoo", "NSE", "BSE"],
    "Valuation Assessment": ["Groww", "Yahoo", "IndianAPI", "Historical multiples"],
    "Business Quality Assessment": ["Groww", "IndianAPI", "Filings"],
    "Financial Health Assessment": ["Groww", "IndianAPI", "Filings"],
    "Risk Assessment": ["Yahoo", "FRED", "NSE"],
    "Portfolio Decision": ["Groww", "Yahoo", "NSE"],
    "Sector Attractiveness": ["NSE", "Yahoo", "IndianAPI"],
    "Industry Structure": ["IndianAPI", "Filings", "NSE"],
    "Macro Impact": ["RBI", "FRED", "IMF", "Yahoo"],
    "Historical Analysis": ["Groww", "IndianAPI", "Yahoo", "Historical multiples"],
    "Peer Comparison": ["Groww", "Yahoo", "IndianAPI"],
    "Scenario Analysis": ["FRED", "IMF", "Yahoo", "Groww"],
    "Forecast": ["Yahoo", "FRED", "Groww"],
    "News Impact": ["NewsAPI", "IndianAPI"],
    "Event Analysis": ["NewsAPI", "NSE", "Filings"],
    "Screening": ["Groww", "IndianAPI", "NSE"],
    "Educational": [],
    "Technical Analysis": ["Yahoo", "NSE"],
    "Accounting Review": ["Filings", "IndianAPI"],
    "Management Assessment": ["Filings", "IndianAPI"],
    "Ownership Review": ["NSE", "IndianAPI", "Filings"],
    "Governance Review": ["Filings", "SEBI"],
    "Policy Analysis": ["RBI", "IMF", "Government"],
    "Regulatory Analysis": ["RBI", "SEBI", "IMF"],
}


def plan_apis(primary_objective: str | None) -> dict[str, Any]:
    apis = list(_MAP.get(primary_objective or "", ["Yahoo"]))
    return {"apis": apis, "api_count": len(apis), "map_version": "roe-v1"}
