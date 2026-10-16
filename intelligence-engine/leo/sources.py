"""Dynamic API / source planner — select only sources required by the Evidence Plan."""

from __future__ import annotations

import os
from typing import Any


# Source catalog: id → capabilities + env keys that mark "configured"
SOURCE_CATALOG: dict[str, dict[str, Any]] = {
    "groww": {
        "category": "market_data",
        "env": ("GROWW_ACCESS_TOKEN", "GROWW_API_KEY"),
        "via": "agib",
        "path": "/api/market/ticker",
        "evidence_types": ("market_data", "valuation_metrics"),
    },
    "indianapi": {
        "category": "market_data",
        "env": ("INDIANAPI_KEY", "INDIAN_API_KEY", "VITE_INDIANAPI_KEY"),
        "via": "market_data|agib",
        "evidence_types": ("market_data", "corporate_announcement", "financial_statements"),
    },
    "finnhub": {
        "category": "market_data",
        "env": ("FINNHUB_API_KEY",),
        "via": "market_data",
        "evidence_types": ("market_data", "valuation_metrics"),
    },
    "twelve_data": {
        "category": "market_data",
        "env": ("TWELVE_DATA_API_KEY",),
        "via": "agib",
        "path": "/api/market/pre-market-briefing",
        "evidence_types": ("market_data",),
    },
    "fmp": {
        "category": "market_data",
        "env": ("FMP_API_KEY",),
        "via": "market_data",
        "evidence_types": ("market_data", "financial_statements", "valuation_metrics"),
    },
    "yahoo": {
        "category": "market_data",
        "env": (),
        "via": "market_data",
        "evidence_types": (
            "market_data",
            "financial_statements",
            "valuation_metrics",
            "corporate_announcement",
        ),
        "always_soft": True,  # flag-gated in YahooFinanceProvider.is_configured
    },
    "fred": {
        "category": "macro",
        "env": ("FRED_API_KEY",),
        "via": "agib",
        "path": "/api/market/macro-briefing",
        "evidence_types": ("macro",),
    },
    "alphavantage": {
        "category": "macro",
        "env": ("ALPHAVANTAGE_API_KEY",),
        "via": "agib",
        "path": "/api/market/macro-briefing",
        "evidence_types": ("macro",),
    },
    "rbi": {
        "category": "macro",
        "env": ("RBI_DATA_API_KEY",),  # optional; AOI also has public RBI
        "via": "aoi|agib",
        "evidence_types": ("macro",),
        "always_soft": True,  # AOI RBI connector available without key
    },
    "nse": {
        "category": "corporate",
        "env": (),
        "via": "aoi",
        "evidence_types": ("corporate_announcement", "quarterly_results", "annual_report"),
        "always_soft": True,
    },
    "bse": {
        "category": "corporate",
        "env": (),
        "via": "aoi",
        "evidence_types": ("corporate_announcement",),
        "always_soft": True,
    },
    "company_ir": {
        "category": "corporate",
        "env": (),
        "via": "aoi",
        "evidence_types": (
            "annual_report",
            "quarterly_results",
            "investor_presentation",
            "earnings_transcript",
            "esg_report",
            "financial_statements",
        ),
        "always_soft": True,
    },
    "newsapi": {
        "category": "news",
        "env": ("NEWSAPI_KEY",),
        "via": "agib",
        "path": "/api/news/headlines",
        "evidence_types": ("news",),
    },
    "internal_research": {
        "category": "research",
        "env": (),
        "via": "kip|eve",
        "evidence_types": ("peer_comparison", "sector_kpis", "valuation_metrics"),
        "always_soft": True,
    },
}


def _env_set(keys: tuple[str, ...]) -> bool:
    return any(bool(os.environ.get(k)) for k in keys)


def configured_sources() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for sid, meta in SOURCE_CATALOG.items():
        keys = tuple(meta.get("env") or ())
        configured = bool(meta.get("always_soft")) or _env_set(keys) or (not keys)
        # Also check Settings for IE-native keys
        if not configured:
            try:
                from app.core.config import get_settings

                s = get_settings()
                for k in keys:
                    attr = k.lower()
                    if getattr(s, attr, None):
                        configured = True
                        break
                    # indian_api_key vs INDIAN_API_KEY
                    if k == "INDIAN_API_KEY" and getattr(s, "indian_api_key", ""):
                        configured = True
                    if k == "FINNHUB_API_KEY" and getattr(s, "finnhub_api_key", ""):
                        configured = True
                    if k == "FMP_API_KEY" and getattr(s, "fmp_api_key", ""):
                        configured = True
            except Exception:
                pass
        out[sid] = {
            **meta,
            "source_id": sid,
            "configured": configured,
            "healthy": configured,  # updated after fetch attempts
        }
    return out


def select_sources(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Select only sources that can satisfy required/optional evidence types."""
    needed = set(plan.get("required_evidence") or []) | set(plan.get("optional_evidence") or [])
    intent = plan.get("intent") or "general_finance"
    catalog = configured_sources()
    selected: list[dict[str, Any]] = []

    for sid, meta in catalog.items():
        caps = set(meta.get("evidence_types") or [])
        if not (caps & needed):
            continue
        # Intent filters
        if intent == "macro" and meta["category"] not in {"macro", "market_data", "research"}:
            continue
        if intent == "news" and meta["category"] not in {"news", "corporate", "market_data"}:
            continue
        if intent == "investment_recommendation" and meta["category"] == "news" and sid == "newsapi":
            # skip general news for investment unless explicitly news intent
            continue
        selected.append({"source_id": sid, **meta, "selected_for": sorted(caps & needed)})
    return selected
