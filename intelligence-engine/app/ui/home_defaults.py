"""Institutional desk defaults for Investment Office homepage — never blank widgets."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any


def _iso(days: int = 0, hours: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()


DEFAULT_THEMES: list[dict[str, Any]] = [
    {
        "id": "credit_growth",
        "name": "Credit Growth",
        "trend": "Constructive",
        "bias": "Overweight",
        "confidence": 0.72,
        "tickers": ["ICICIBANK", "HDFCBANK", "BAJFINANCE"],
        "related_companies": ["ICICIBANK", "HDFCBANK", "BAJFINANCE"],
    },
    {
        "id": "defence",
        "name": "Defence",
        "trend": "Momentum",
        "bias": "Overweight",
        "confidence": 0.68,
        "tickers": ["HAL", "BEL", "BDL"],
        "related_companies": ["HAL", "BEL", "BDL"],
    },
    {
        "id": "ai_digital",
        "name": "AI & Digital",
        "trend": "Forming",
        "bias": "Selective",
        "confidence": 0.61,
        "tickers": ["TCS", "INFY", "HCLTECH"],
        "related_companies": ["TCS", "INFY", "HCLTECH"],
    },
    {
        "id": "power_capex",
        "name": "Power & Capex",
        "trend": "Constructive",
        "bias": "Overweight",
        "confidence": 0.66,
        "tickers": ["NTPC", "POWERGRID", "LT"],
        "related_companies": ["NTPC", "POWERGRID", "LT"],
    },
    {
        "id": "consumption",
        "name": "Domestic Consumption",
        "trend": "Watch",
        "bias": "Neutral",
        "confidence": 0.54,
        "tickers": ["TITAN", "ASIANPAINT", "ITC"],
        "related_companies": ["TITAN", "ASIANPAINT", "ITC"],
    },
    {
        "id": "energy_transition",
        "name": "Energy Transition",
        "trend": "Constructive",
        "bias": "Selective",
        "confidence": 0.58,
        "tickers": ["RELIANCE", "ONGC", "NTPC"],
        "related_companies": ["RELIANCE", "ONGC", "NTPC"],
    },
    {
        "id": "rate_sensitive",
        "name": "Rate Sensitive",
        "trend": "Policy-linked",
        "bias": "Watch",
        "confidence": 0.57,
        "tickers": ["LICHSGFIN", "DLF", "INDUSINDBK"],
        "related_companies": ["LICHSGFIN", "DLF", "INDUSINDBK"],
    },
]

DEFAULT_COMPANIES: list[dict[str, Any]] = [
    {"ticker": "RELIANCE", "label": "Overweight", "confidence": 0.74, "score": 84, "sector": "Energy"},
    {"ticker": "ICICIBANK", "label": "Overweight", "confidence": 0.78, "score": 86, "sector": "Financials"},
    {"ticker": "HDFCBANK", "label": "Neutral", "confidence": 0.62, "score": 71, "sector": "Financials"},
    {"ticker": "TCS", "label": "Selective", "confidence": 0.64, "score": 73, "sector": "IT"},
    {"ticker": "INFY", "label": "Selective", "confidence": 0.60, "score": 69, "sector": "IT"},
    {"ticker": "HAL", "label": "Overweight", "confidence": 0.71, "score": 79, "sector": "Defence"},
    {"ticker": "BEL", "label": "Overweight", "confidence": 0.69, "score": 77, "sector": "Defence"},
    {"ticker": "LT", "label": "Constructive", "confidence": 0.67, "score": 75, "sector": "Industrials"},
]

DEFAULT_RESEARCH: list[dict[str, Any]] = [
    {
        "id": "agi-house-banks",
        "title": "Private Banks: Credit Growth Still Supports Selective Overweight",
        "category": "Financials",
        "summary": "Deposit costs and loan growth remain the swing factors. Prefer franchises with liability strength.",
        "read_time": "6 min",
        "house_view": "Selective Overweight",
        "as_of": _iso(-1),
        "href": "/ask?q=Should%20I%20invest%20in%20ICICI%20Bank%3F",
        "tickers": ["ICICIBANK", "HDFCBANK"],
    },
    {
        "id": "agi-house-defence",
        "title": "Defence Theme: Order Book Visibility Remains Institutional",
        "category": "Defence",
        "summary": "Domestic order pipeline and export optionality keep the theme constructive into the next budget cycle.",
        "read_time": "5 min",
        "house_view": "Overweight",
        "as_of": _iso(-2),
        "href": "/themes/defence",
        "tickers": ["HAL", "BEL"],
    },
    {
        "id": "agi-house-macro",
        "title": "Rates, Liquidity and the Path for Domestic Cyclicals",
        "category": "Macro",
        "summary": "Policy tone and real rates still dominate sector leadership. Stay selective in rate-sensitive names.",
        "read_time": "7 min",
        "house_view": "Cautious Constructive",
        "as_of": _iso(0),
        "href": "/macro-intelligence",
        "tickers": [],
    },
    {
        "id": "agi-house-it",
        "title": "IT Services: Deal Pipeline Steady, Pricing Still the Watchpoint",
        "category": "IT",
        "summary": "Large-deal commentary supports selective exposure; margin recovery remains uneven across the pack.",
        "read_time": "5 min",
        "house_view": "Selective",
        "as_of": _iso(-3),
        "href": "/themes/ai_digital",
        "tickers": ["TCS", "INFY"],
    },
]

DEFAULT_PREDICTIONS: list[dict[str, Any]] = [
    {
        "id": "pred-icici-12m",
        "ticker": "ICICIBANK",
        "thesis": "Franchise deposit strength supports above-system loan growth over the next 12 months.",
        "current_status": "open",
        "confidence": 0.76,
        "target_horizon": "12 months",
        "current_return": "+4.2%",
        "target_date": (date.today() + timedelta(days=365)).isoformat(),
        "publication_date": _iso(-10),
    },
    {
        "id": "pred-hal-18m",
        "ticker": "HAL",
        "thesis": "Defence order conversion and export options can sustain earnings visibility through FY27.",
        "current_status": "open",
        "confidence": 0.71,
        "target_horizon": "18 months",
        "current_return": "+9.1%",
        "target_date": (date.today() + timedelta(days=540)).isoformat(),
        "publication_date": _iso(-18),
    },
    {
        "id": "pred-reliance-12m",
        "ticker": "RELIANCE",
        "thesis": "Retail + digital cash flows remain the core re-rating path while energy stabilises.",
        "current_status": "open",
        "confidence": 0.68,
        "target_horizon": "12 months",
        "current_return": "+2.4%",
        "target_date": (date.today() + timedelta(days=365)).isoformat(),
        "publication_date": _iso(-7),
    },
    {
        "id": "pred-tcs-9m",
        "ticker": "TCS",
        "thesis": "Deal pipeline quality supports a selective recovery if pricing pressure eases.",
        "current_status": "watch",
        "confidence": 0.59,
        "target_horizon": "9 months",
        "current_return": "-1.1%",
        "target_date": (date.today() + timedelta(days=270)).isoformat(),
        "publication_date": _iso(-14),
    },
    {
        "id": "pred-lt-12m",
        "ticker": "LT",
        "thesis": "Domestic capex and infra awarding continue to underpin medium-term order inflow.",
        "current_status": "open",
        "confidence": 0.70,
        "target_horizon": "12 months",
        "current_return": "+6.3%",
        "target_date": (date.today() + timedelta(days=365)).isoformat(),
        "publication_date": _iso(-5),
    },
]


def default_calendar() -> list[dict[str, Any]]:
    today = date.today()
    return [
        {
            "id": "cal-cpi",
            "title": "India CPI",
            "name": "India CPI",
            "country": "IN",
            "region": "India",
            "importance": "High",
            "expected_impact": "Inflation path shapes RBI room and rate-sensitive sector leadership.",
            "affected_sectors": ["Banks", "Autos", "FMCG"],
            "affected_companies": ["HDFCBANK", "MARUTI", "ITC"],
            "as_of": (today + timedelta(days=1)).isoformat(),
            "date": (today + timedelta(days=1)).isoformat(),
            "when": "Tomorrow",
        },
        {
            "id": "cal-rbi",
            "title": "RBI MPC Decision",
            "name": "RBI MPC Decision",
            "country": "IN",
            "region": "India",
            "importance": "High",
            "expected_impact": "Policy language matters as much as the action for financial conditions.",
            "affected_sectors": ["Banks", "NBFCs", "Real Estate"],
            "affected_companies": ["ICICIBANK", "BAJFINANCE", "DLF"],
            "as_of": (today + timedelta(days=5)).isoformat(),
            "date": (today + timedelta(days=5)).isoformat(),
            "when": "This Week",
        },
        {
            "id": "cal-pce",
            "title": "US Core PCE",
            "name": "US Core PCE",
            "country": "US",
            "region": "United States",
            "importance": "High",
            "expected_impact": "Global yields and the dollar transmit into Indian risk appetite.",
            "affected_sectors": ["IT", "Financials", "Metals"],
            "affected_companies": ["TCS", "INFY", "TATASTEEL"],
            "as_of": (today + timedelta(days=2)).isoformat(),
            "date": (today + timedelta(days=2)).isoformat(),
            "when": "This Week",
        },
        {
            "id": "cal-gdp",
            "title": "India GDP / PMI cluster",
            "name": "India GDP / PMI",
            "country": "IN",
            "region": "India",
            "importance": "Medium",
            "expected_impact": "Growth confirmation supports domestic cyclicals if inflation stays contained.",
            "affected_sectors": ["Industrials", "Banks", "Consumption"],
            "affected_companies": ["LT", "ICICIBANK", "TITAN"],
            "as_of": (today + timedelta(days=4)).isoformat(),
            "date": (today + timedelta(days=4)).isoformat(),
            "when": "This Week",
        },
        {
            "id": "cal-nfp",
            "title": "US Employment",
            "name": "US Employment",
            "country": "US",
            "region": "United States",
            "importance": "High",
            "expected_impact": "Labour data can reprice global financial conditions quickly.",
            "affected_sectors": ["IT", "Banks", "Metals"],
            "affected_companies": ["TCS", "HDFCBANK", "HINDALCO"],
            "as_of": (today + timedelta(days=6)).isoformat(),
            "date": (today + timedelta(days=6)).isoformat(),
            "when": "This Week",
        },
        {
            "id": "cal-oil",
            "title": "OPEC / oil supply updates",
            "name": "OPEC / oil supply",
            "country": "GLOBAL",
            "region": "Global",
            "importance": "High",
            "expected_impact": "Oil remains the fastest macro shock channel for India.",
            "affected_sectors": ["Energy", "Airlines", "Chemicals"],
            "affected_companies": ["RELIANCE", "ONGC", "INDIGO"],
            "as_of": (today + timedelta(days=8)).isoformat(),
            "date": (today + timedelta(days=8)).isoformat(),
            "when": "Next Week",
        },
    ]


def default_newsletter() -> dict[str, Any]:
    return {
        "subscribers": "12.4k",
        "research_published": 186,
        "last_newsletter": "AGI Weekly Intelligence",
        "next_release": "Sunday 08:00 IST",
    }


def default_footer_metrics() -> dict[str, Any]:
    return {
        "research_coverage": 48,
        "companies_covered": 120,
        "predictions": 64,
        "research_articles": 186,
        "knowledge_nodes": 940,
        "data_points": 12840,
        "research_since": "2024",
        "broker_reports": 312,
        "themes": 28,
        "sectors": 18,
        "knowledge_documents": 640,
    }


def fill_list(primary: list | None, fallback: list, *, min_items: int = 1) -> list:
    rows = [r for r in (primary or []) if r]
    if len(rows) >= min_items:
        return rows
    seen = set()
    out: list[Any] = []
    for row in list(rows) + list(fallback):
        key = None
        if isinstance(row, dict):
            key = row.get("id") or row.get("ticker") or row.get("question") or row.get("title") or row.get("name")
        else:
            key = str(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= max(min_items, len(fallback)):
            break
    return out or list(fallback)
