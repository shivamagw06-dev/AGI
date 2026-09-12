"""Versioned IEW weight profile v1.0.0 — deterministic, no LLM.

Max component weights sum to 100 (institutional scorecard style):
  Credibility 40 · Materiality 22 · Freshness 10 · Quality 8 ·
  Corroboration 8 · Analogue 6 · Specificity 6
"""

from __future__ import annotations

from typing import Any

PROFILE_ID = "iew-weight-profile-v1.0.0"
PROFILE_VERSION = "1.0.0"

# Caps (must sum to 100 for normalised scorecard readability)
CAPS: dict[str, float] = {
    "credibility": 40.0,
    "materiality": 22.0,
    "freshness": 10.0,
    "quality": 8.0,
    "corroboration": 8.0,
    "analogue": 6.0,
    "specificity": 6.0,
}

# Source credibility tiers → fraction of credibility cap (0..1)
SOURCE_CREDIBILITY: dict[str, float] = {
    # Highest institutional trust
    "audited_filing": 1.00,
    "annual_report": 0.98,
    "exchange_filing": 0.96,
    "quarterly_results": 0.94,
    "regulator": 0.93,
    "government_notification": 0.92,
    "sebi": 0.93,
    "rbi": 0.93,
    "mca": 0.90,
    "company_ir": 0.82,
    "conference_call": 0.78,
    "investor_presentation": 0.74,
    "reuters": 0.62,
    "bloomberg": 0.62,
    "broker_research": 0.55,
    "industry_research": 0.52,
    "general_media": 0.35,
    "social_media": 0.12,
    "rumour": 0.05,
    # Synthetic / fixtures — never dominate live evidence
    "fixture": 0.08,
    "seed": 0.10,
    "synthetic": 0.06,
    "estimated": 0.20,
    "derived": 0.28,
    "unknown": 0.25,
}

# Alias normalisation → canonical key
SOURCE_ALIASES: dict[str, str] = {
    "audited": "audited_filing",
    "filing": "exchange_filing",
    "nse": "exchange_filing",
    "bse": "exchange_filing",
    "sec": "exchange_filing",
    "10-k": "annual_report",
    "10k": "annual_report",
    "10-q": "quarterly_results",
    "10q": "quarterly_results",
    "ar": "annual_report",
    "annual": "annual_report",
    "quarterly": "quarterly_results",
    "earnings": "quarterly_results",
    "ir": "company_ir",
    "investor_relations": "company_ir",
    "press_release": "company_ir",
    "transcript": "conference_call",
    "call": "conference_call",
    "ppt": "investor_presentation",
    "deck": "investor_presentation",
    "media": "general_media",
    "news": "general_media",
    "twitter": "social_media",
    "x": "social_media",
    "reddit": "social_media",
    "gov": "government_notification",
    "gazette": "government_notification",
    "regulatory": "regulator",
    "broker": "broker_research",
    "sellside": "broker_research",
    "industry": "industry_research",
    "analog": "unknown",
    "analogue": "unknown",
    "memory": "unknown",
    "imai": "unknown",
    "ieg": "unknown",
    "iere": "unknown",
    "knowledge_factory": "unknown",
    "kf": "unknown",
}

MATERIALITY_FRACTION: dict[str, float] = {
    "direct": 1.00,
    "supporting": 0.70,
    "context": 0.40,
    "peripheral": 0.15,
    "unknown": 0.35,
}

FRESHNESS_FRACTION: dict[str, float] = {
    "current": 1.00,  # <= 90d
    "recent": 0.75,  # <= 365d
    "historical": 0.40,
    "replay_safe": 0.55,  # historical but TIRC-allowed
    "stale": 0.20,
    "unknown": 0.45,
}

QUALITY_FRACTION: dict[str, float] = {
    "audited": 1.00,
    "primary": 0.90,
    "secondary": 0.55,
    "derived": 0.35,
    "estimated": 0.25,
    "synthetic": 0.08,
    "fixture": 0.05,
    "seed": 0.10,
    "unknown": 0.40,
}

SPECIFICITY_FRACTION: dict[str, float] = {
    "company": 1.00,
    "business_unit": 0.85,
    "segment": 0.75,
    "industry": 0.50,
    "macro": 0.35,
    "general": 0.20,
    "unknown": 0.40,
}

# Floor: fixtures/synthetic cannot exceed this absolute weight unless alone
FIXTURE_CEILING = 25.0
LIVE_VALIDATED_FLOOR_OVER_FIXTURE = 15.0  # live must beat fixture by this margin when both present

PROFILE: dict[str, Any] = {
    "profile_id": PROFILE_ID,
    "version": PROFILE_VERSION,
    "caps": CAPS,
    "source_credibility": SOURCE_CREDIBILITY,
    "source_aliases": SOURCE_ALIASES,
    "materiality": MATERIALITY_FRACTION,
    "freshness": FRESHNESS_FRACTION,
    "quality": QUALITY_FRACTION,
    "specificity": SPECIFICITY_FRACTION,
    "fixture_ceiling": FIXTURE_CEILING,
    "live_validated_floor_over_fixture": LIVE_VALIDATED_FLOOR_OVER_FIXTURE,
    "deterministic": True,
    "llm_used": False,
}
