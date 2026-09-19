"""Valuation status labels — analysis language only, never BUY/SELL."""

from __future__ import annotations

from typing import Any, Optional


def valuation_status(
    *,
    percentile: Optional[float],
    premium_pct: Optional[float],
    primary_value: Optional[float],
    policy_status: Optional[str] = None,
    provider_coverage: int = 0,
) -> str:
    ps = str(policy_status or "").upper()
    if ps in {"METRIC_NOT_APPLICABLE", "NOT_APPLICABLE", "HIDDEN"}:
        return "Metric Not Applicable"
    if primary_value is None and provider_coverage <= 0:
        return "Data Insufficient"
    if percentile is not None:
        if percentile <= 15:
            return "Historically Cheap"
        if percentile <= 35:
            return "Undervalued"
        if percentile >= 85:
            return "Historically Expensive"
        if percentile >= 65:
            return "Premium"
        return "Fairly Valued"
    if premium_pct is not None:
        if premium_pct <= -20:
            return "Undervalued"
        if premium_pct >= 25:
            return "Premium"
        return "Fairly Valued"
    return "Data Insufficient"


def opportunity_label(percentile: Optional[float]) -> str:
    if percentile is None:
        return "Unknown"
    if percentile <= 30:
        return "Attractive"
    if percentile >= 70:
        return "Premium"
    return "Fair"


def outcome_label(percentile: Optional[float], premium_pct: Optional[float]) -> str:
    if percentile is None and premium_pct is None:
        return "Insufficient History"
    if percentile is not None:
        if percentile >= 80:
            return "Fairly Expensive"
        if percentile >= 60:
            return "Mild Premium"
        if percentile <= 20:
            return "Historically Attractive"
        if percentile <= 40:
            return "Mild Discount"
        return "Near Fair Value"
    if premium_pct is not None:
        if premium_pct >= 20:
            return "Fairly Expensive"
        if premium_pct <= -15:
            return "Historically Attractive"
        return "Near Fair Value"
    return "Near Fair Value"


def market_cap_bucket(market_cap: Optional[float]) -> Optional[str]:
    """Rough INR buckets from warehouse market_cap (rupees)."""
    if market_cap is None:
        return None
    # 20,000 cr / 5,000 cr thresholds
    if market_cap >= 2e11:
        return "large"
    if market_cap >= 5e10:
        return "mid"
    return "small"
