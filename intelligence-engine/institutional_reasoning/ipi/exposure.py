"""Module 4 — Exposure Intelligence.

Tracks sector/industry/country/currency/factor/theme exposures and rejects
policy breaches.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ipi.portfolio_book import default_book, holding_for, sector_weight
from institutional_reasoning.ipi.schema import DEFAULT_POLICY

EXPOSURE_VERSION = "exposure-intelligence-v1.0.0"

# Candidate metadata when not already in the book.
_CANDIDATE_META: dict[str, dict[str, Any]] = {
    "INFY": {"sector": "it_services", "industry": "it_services", "country": "IN", "currency": "INR", "theme": "ai_services", "market_cap": "large",
             "factors": {"quality": 0.85, "value": 0.4, "growth": 0.5, "momentum": 0.4}},
    "TCS": {"sector": "it_services", "industry": "it_services", "country": "IN", "currency": "INR", "theme": "ai_services", "market_cap": "large",
            "factors": {"quality": 0.9, "value": 0.35, "growth": 0.45, "momentum": 0.35}},
    "WIPRO": {"sector": "it_services", "industry": "it_services", "country": "IN", "currency": "INR", "theme": "ai_services", "market_cap": "large",
              "factors": {"quality": 0.7, "value": 0.5, "growth": 0.4, "momentum": 0.35}},
    "HDFCBANK": {"sector": "banks", "industry": "private_bank", "country": "IN", "currency": "INR", "theme": "financials", "market_cap": "large",
                 "factors": {"quality": 0.8, "value": 0.4, "growth": 0.5, "momentum": 0.3}},
    "ZOMATO": {"sector": "consumer_internet", "industry": "food_delivery", "country": "IN", "currency": "INR", "theme": "platform", "market_cap": "mid",
               "factors": {"quality": 0.4, "value": 0.2, "growth": 0.85, "momentum": 0.7}},
    "PERSISTENT": {"sector": "it_services", "industry": "it_services", "country": "IN", "currency": "INR", "theme": "ai_services", "market_cap": "mid",
                   "factors": {"quality": 0.7, "value": 0.3, "growth": 0.75, "momentum": 0.6}},
}


def _meta(symbol: str, book: dict[str, Any]) -> dict[str, Any]:
    h = holding_for(symbol, book) or {}
    base = dict(_CANDIDATE_META.get(symbol.upper(), {}))
    base.update({k: v for k, v in h.items() if v is not None})
    base.setdefault("sector", "unknown")
    base.setdefault("industry", base.get("sector"))
    base.setdefault("country", "IN")
    base.setdefault("currency", "INR")
    base.setdefault("market_cap", "large")
    base.setdefault("theme", "")
    base.setdefault("factors", {})
    return base


def _bucket_weights(holdings: list[dict[str, Any]], key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for h in holdings:
        k = str(h.get(key) or "unknown")
        out[k] = round(out.get(k, 0.0) + float(h.get("weight") or 0.0), 6)
    return out


def compute_exposure(
    *,
    entity_id: str | None,
    proposed_weight: float | None = None,
    book: dict[str, Any] | None = None,
) -> dict[str, Any]:
    book = book or default_book()
    symbol = str(entity_id or "").upper()
    meta = _meta(symbol, book) if symbol else {}
    holdings = list(book.get("holdings") or [])
    current = holding_for(symbol, book)
    current_w = float((current or {}).get("weight") or 0.0)
    target_w = float(proposed_weight) if proposed_weight is not None else current_w

    sector = str(meta.get("sector") or "unknown")
    sector_now = sector_weight(sector, book)
    # Impact if we set candidate to target_w (replace current weight)
    sector_after = round(sector_now - current_w + target_w, 6)

    country = str(meta.get("country") or "IN")
    theme = str(meta.get("theme") or "")
    country_now = sum(float(h.get("weight") or 0) for h in holdings if str(h.get("country") or "IN") == country)
    country_after = round(country_now - current_w + target_w, 6)
    theme_now = sum(float(h.get("weight") or 0) for h in holdings if str(h.get("theme") or "") == theme and theme)
    theme_after = round(theme_now - current_w + target_w, 6) if theme else 0.0

    policy = book.get("policy") or DEFAULT_POLICY.to_dict()
    breaches: list[dict[str, Any]] = []
    if sector_after > float(policy.get("max_sector_weight") or 0.25) + 1e-9:
        breaches.append(
            {
                "kind": "sector",
                "limit": policy.get("max_sector_weight"),
                "projected": sector_after,
                "message": f"Sector {sector} > policy limit",
            }
        )
    if country_after > float(policy.get("max_country_weight") or 0.90) + 1e-9:
        breaches.append(
            {
                "kind": "country",
                "limit": policy.get("max_country_weight"),
                "projected": country_after,
                "message": f"Country {country} > policy limit",
            }
        )
    if theme and theme_after > float(policy.get("max_theme_weight") or 0.30) + 1e-9:
        breaches.append(
            {
                "kind": "theme",
                "limit": policy.get("max_theme_weight"),
                "projected": theme_after,
                "message": f"Theme {theme} concentration",
            }
        )
    if target_w > float(policy.get("max_stock_weight") or 0.07) + 1e-9:
        breaches.append(
            {
                "kind": "stock",
                "limit": policy.get("max_stock_weight"),
                "projected": target_w,
                "message": f"Stock weight > policy limit",
            }
        )

    factors = meta.get("factors") or {}
    factor_tilt = {
        "growth": float(factors.get("growth") or 0.5),
        "value": float(factors.get("value") or 0.5),
        "quality": float(factors.get("quality") or 0.5),
        "momentum": float(factors.get("momentum") or 0.5),
    }
    # Simple imbalance flag when quality<<growth for a large proposed weight
    if target_w >= 0.05 and factor_tilt["growth"] - factor_tilt["quality"] >= 0.35:
        breaches.append(
            {
                "kind": "factor",
                "limit": "quality_vs_growth",
                "projected": factor_tilt,
                "message": "Factor imbalance: growth dominates quality",
            }
        )

    # Headroom the candidate may occupy before breaching each bucket limit.
    sector_headroom = max(0.0, round(float(policy.get("max_sector_weight") or 0.25) - (sector_now - current_w), 6))
    country_headroom = max(0.0, round(float(policy.get("max_country_weight") or 0.90) - (country_now - current_w), 6))
    theme_headroom = (
        max(0.0, round(float(policy.get("max_theme_weight") or 0.30) - (theme_now - current_w), 6))
        if theme
        else None
    )
    max_allowed_weight = min(
        float(policy.get("max_stock_weight") or 0.07),
        sector_headroom,
        country_headroom,
        theme_headroom if theme_headroom is not None else float("inf"),
    )

    exposure_payload = {
        "symbol": symbol or None,
        "weight": target_w,
        "allocation": target_w,
        "current_weight": current_w,
        "sector": sector,
        "industry": meta.get("industry"),
        "country": country,
        "currency": meta.get("currency"),
        "theme": theme,
        "market_cap": meta.get("market_cap"),
        "sector_weight_now": sector_now,
        "sector_weight_after": sector_after,
        "country_weight_after": country_after,
        "theme_weight_after": theme_after,
        "sector_headroom": sector_headroom,
        "country_headroom": country_headroom,
        "theme_headroom": theme_headroom,
        "max_allowed_weight": round(max_allowed_weight, 6),
        "factors": factor_tilt,
        "sector_buckets": _bucket_weights(holdings, "sector"),
        "country_buckets": _bucket_weights(holdings, "country"),
    }

    return {
        "found": True,
        "exposure_version": EXPOSURE_VERSION,
        "entity_id": symbol or None,
        "exposure": exposure_payload,
        "weight": target_w,
        "allocation": target_w,
        "max_allowed_weight": round(max_allowed_weight, 6),
        "sector_headroom": sector_headroom,
        "breaches": breaches,
        "rejected": bool(breaches),
        "portfolio_fit": 1.0 - min(1.0, 0.25 * len(breaches)),
    }
