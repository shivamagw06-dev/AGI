"""Seeded institutional market domain tips — Sprint 12.1."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MARKET_UNIVERSE

MARKET_CATALOG: dict[str, dict[str, Any]] = {
    "india_equity": {
        "label": "India Equity",
        "regime": "Expansion",
        "summary": "Domestic equities supported by liquidity and earnings resilience",
        "indices": ["NIFTY 50", "SENSEX", "Bank NIFTY", "FINNIFTY", "NIFTY Midcap"],
        "primary_source": "Groww API (ops collection)",
        "risk_sentiment": "Risk On",
        "health_base": 62.0,
        "trend": "Improving",
        "confidence": 0.78,
    },
    "global_equity": {
        "label": "Global Equity",
        "regime": "Sideways",
        "summary": "Developed markets mixed; US leadership concentrated",
        "indices": ["S&P 500", "Nasdaq", "Dow Jones", "FTSE", "DAX", "Nikkei", "Hang Seng"],
        "primary_source": "Yahoo Finance (ops collection)",
        "risk_sentiment": "Mixed",
        "health_base": 55.0,
        "trend": "Stable",
        "confidence": 0.72,
    },
    "breadth": {
        "label": "Market Breadth",
        "regime": "Sideways",
        "summary": "Participation mixed — leadership concentrated in large caps",
        "metrics": {
            "advance_decline_ratio": 1.15,
            "new_highs": 42,
            "new_lows": 18,
            "participation_pct": 58.0,
            "equal_weight_strength": "Mixed",
            "sector_breadth": "Moderate",
        },
        "risk_sentiment": "Mixed",
        "health_base": 56.0,
        "trend": "Stable",
        "confidence": 0.74,
    },
    "liquidity": {
        "label": "Market Liquidity",
        "regime": "Expansion",
        "summary": "Turnover adequate; delivery supportive on leaders",
        "metrics": {
            "trading_volume": "Adequate",
            "delivery_volume": "Supportive",
            "turnover": "Healthy",
            "order_book": "Balanced",
            "institutional_activity": "Active",
        },
        "risk_sentiment": "Risk On",
        "health_base": 64.0,
        "trend": "Improving",
        "confidence": 0.76,
    },
    "volatility": {
        "label": "Market Volatility",
        "regime": "Sideways",
        "summary": "Realized volatility contained; no stress spike",
        "metrics": {
            "realized_volatility": "Contained",
            "atr_state": "Normal",
            "index_volatility": "Low-Moderate",
            "sector_volatility": "Selective",
        },
        "risk_sentiment": "Risk On",
        "health_base": 68.0,
        "trend": "Stable",
        "confidence": 0.75,
    },
    "institutional_flows": {
        "label": "Institutional Flows",
        "regime": "Expansion",
        "summary": "DII supportive; FII intermittent — net domestic bid",
        "metrics": {
            "fii_activity": "Intermittent",
            "dii_activity": "Supportive",
            "etf_activity": "Steady",
            "mutual_fund_flow": "Positive",
        },
        "risk_sentiment": "Risk On",
        "health_base": 60.0,
        "trend": "Improving",
        "confidence": 0.7,
    },
    "leadership": {
        "label": "Market Leadership",
        "regime": "Expansion",
        "summary": "Financials and capital goods lead; IT selective",
        "leading_sectors": ["Banking", "Capital Goods", "Auto"],
        "weak_sectors": ["IT Services", "FMCG"],
        "leading_stocks": ["HDFCBANK", "LT", "MARUTI"],
        "weak_stocks": ["INFY"],
        "rotation": "Cyclical / domestic leadership",
        "risk_sentiment": "Growth Rotation",
        "health_base": 63.0,
        "trend": "Improving",
        "confidence": 0.77,
    },
    "cross_asset": {
        "label": "Cross Asset State",
        "regime": "Sideways",
        "summary": "Equities constructive; gold bid; oil range-bound; USDINR soft",
        "metrics": {
            "equities": "Constructive",
            "bonds": "Stable",
            "gold": "Bid",
            "oil": "Range-bound",
            "usd": "Firm",
            "usdinr": "Soft bias",
            "commodities": "Mixed",
        },
        "risk_sentiment": "Mixed",
        "health_base": 58.0,
        "trend": "Stable",
        "confidence": 0.71,
    },
    "risk_sentiment": {
        "label": "Risk Sentiment",
        "regime": "Expansion",
        "summary": "Risk-on bias with selective defensive hedges",
        "risk_sentiment": "Risk On",
        "health_base": 61.0,
        "trend": "Improving",
        "confidence": 0.73,
    },
    "market_health": {
        "label": "Market Health",
        "regime": "Expansion",
        "summary": "Composite health supported by liquidity and leadership",
        "components": ["breadth", "liquidity", "leadership", "volatility", "institutional_flows", "risk_sentiment"],
        "risk_sentiment": "Risk On",
        "health_base": 62.0,
        "trend": "Improving",
        "confidence": 0.8,
    },
}


def assert_catalog_complete() -> None:
    missing = [k for k in MARKET_UNIVERSE if k not in MARKET_CATALOG]
    if missing:
        raise AssertionError(f"MARKET_CATALOG missing domains: {missing}")


def catalog_for(domain_key: str) -> dict[str, Any]:
    return dict(MARKET_CATALOG.get(domain_key) or {})
