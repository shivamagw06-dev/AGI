"""Yahoo Finance gateway — fundamentals, statements, research (not live LTP primary)."""

from __future__ import annotations

import os
import time
from typing import Any

from forecast_provider_integration.schema import StaticKnowledge, utc_now

_SEEDED_STATIC: dict[str, dict[str, Any]] = {
    "INFY": {
        "business_profile": {
            "name": "Infosys Limited",
            "sector": "Information Technology",
            "industry": "IT Services",
            "employees": 250000,
            "summary": "Global digital services and consulting",
            "market_cap_tip": "large_cap",
            "beta_tip": 0.85,
        },
        "financial_statements": {
            "income_statement": {"revenue_growth_tip": "mid_single_digit", "period": "annual"},
            "balance_sheet": {"net_cash": True},
            "cash_flow": {"fcf_quality": "high"},
            "quarterly": True,
            "annual": True,
        },
        "historical_financials": {"years": 10, "source": "yahoo"},
        "historical_valuation": {"pe_band": "premium", "source": "yahoo"},
        "historical_ratios": {"roe_tip": "high", "margins": "stable_to_up"},
        "historical_ownership": {"institutional": "high", "promoter": "moderate"},
        "research": {
            "earnings_dates": True,
            "eps_trends": "stable",
            "analyst_estimates": True,
            "recommendations": "hold_cluster",
            "news": True,
        },
    },
    "TCS": {
        "business_profile": {
            "name": "Tata Consultancy Services",
            "sector": "Information Technology",
            "industry": "IT Services",
            "employees": 600000,
            "summary": "Largest Indian IT services franchise",
        },
        "financial_statements": {"income_statement": {"period": "annual"}, "quarterly": True},
        "historical_financials": {"years": 10},
        "historical_valuation": {"pe_band": "quality_premium"},
        "historical_ratios": {"roe_tip": "high"},
        "historical_ownership": {"promoter": "high"},
        "research": {"earnings_dates": True, "recommendations": "hold_cluster"},
    },
    "HDFCBANK": {
        "business_profile": {
            "name": "HDFC Bank",
            "sector": "Financials",
            "industry": "Private Bank",
            "summary": "Leading private sector bank",
        },
        "financial_statements": {"income_statement": {"period": "annual"}, "quarterly": True},
        "historical_financials": {"years": 10},
        "historical_valuation": {"pe_band": "mid_cycle"},
        "historical_ratios": {"nim_tip": "watch"},
        "historical_ownership": {"institutional": "high"},
        "research": {"earnings_dates": True, "recommendations": "accumulate_cluster"},
    },
    "RELIANCE": {
        "business_profile": {
            "name": "Reliance Industries",
            "sector": "Energy",
            "industry": "Conglomerate",
            "summary": "Energy, retail, digital",
        },
        "financial_statements": {"income_statement": {"period": "annual"}, "quarterly": True},
        "historical_financials": {"years": 10},
        "historical_valuation": {"pe_band": "sum_of_parts"},
        "historical_ratios": {"segment_dependent": True},
        "historical_ownership": {"promoter": "high"},
        "research": {"earnings_dates": True},
    },
}


class YahooFinancialGateway:
    provider = "yahoo"

    def health(self) -> dict[str, Any]:
        # Yahoo is soft-always available via fixture / MD client; never polled every few seconds
        yf_flag = (os.environ.get("YAHOO_FINANCE_ENABLED") or "1").strip().lower()
        enabled = yf_flag not in {"0", "false", "no"}
        return {
            "provider": self.provider,
            "configured": enabled,
            "connection": "research_path",
            "websocket": False,
            "role": "research_and_historical",
            "status": "healthy" if enabled else "unavailable",
            "detail": "Daily/event fundamentals — never sub-second polling",
            "poll_interval_forbidden_sec": 5,
        }

    def fetch_static(self, entity: str) -> StaticKnowledge:
        t0 = time.perf_counter()
        key = entity.upper()
        raw = dict(_SEEDED_STATIC.get(key) or {
            "business_profile": {"name": key, "sector": "Unknown"},
            "financial_statements": {},
            "historical_financials": {},
            "historical_valuation": {},
            "historical_ratios": {},
            "historical_ownership": {},
            "research": {},
        })
        _ = time.perf_counter() - t0
        now = utc_now()
        return StaticKnowledge(
            business_profile=dict(raw.get("business_profile") or {}),
            financial_statements=dict(raw.get("financial_statements") or {}),
            historical_financials=dict(raw.get("historical_financials") or {}),
            historical_valuation=dict(raw.get("historical_valuation") or {}),
            historical_ratios=dict(raw.get("historical_ratios") or {}),
            historical_ownership=dict(raw.get("historical_ownership") or {}),
            research=dict(raw.get("research") or {}),
            primary_sources=["yahoo"],
            updated_at=now,
            freshness_sec=0,
        )

    def fallback_snapshot_fields(self, entity: str) -> dict[str, Any]:
        """Yahoo fallback for live LTP only when Groww unavailable — sparse quote tip."""
        static = self.fetch_static(entity)
        # Not a full live book — institutional tip only
        return {
            "ltp": None,
            "change_pct": None,
            "source_provider": "yahoo",
            "fallback_used": True,
            "note": "Yahoo quote fallback — secondary to Groww",
            "profile_hint": static.business_profile.get("name"),
        }
