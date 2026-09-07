"""Market Analyst — What is the market saying?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    cid = ctx.get("company_dossier") if isinstance(ctx.get("company_dossier"), dict) else {}
    leo = ctx.get("live_evidence") if isinstance(ctx.get("live_evidence"), dict) else {}
    de = ctx.get("decision_engine") if isinstance(ctx.get("decision_engine"), dict) else {}
    layers = {str(l.get("id")): l for l in (de.get("layers") or []) if isinstance(l, dict)}
    tech = layers.get("technical") or {}
    market = cid.get("market_intelligence") if isinstance(cid.get("market_intelligence"), dict) else {}
    md = cid.get("market_data") if isinstance(cid.get("market_data"), dict) else {}
    src = market or md or {}
    name = company_name(ctx)

    trend = str(src.get("trend") or tech.get("reasoning") or "")
    stance = "Bullish" if any(w in trend.lower() for w in ("construct", "up", "positive", "strong")) else "Neutral"
    if any(w in trend.lower() for w in ("weak", "down", "risk-off", "fragile")):
        stance = "Bearish"

    evidence = as_list(leo.get("market_data_used") or src.get("evidence") or tech.get("evidence"), limit=6)
    if not evidence:
        evidence = ["Price/volume context from institutional market tape", "Liquidity and range cross-checks"]

    score = tech.get("score")
    coverage = pick_confidence(src.get("confidence"), score, default=0.5)
    return structured_opinion(
        role="market",
        summary=f"{name}: tape reflects trend, liquidity, and positioning — a timing overlay only.",
        strengths=as_list([src.get("liquidity") or "Liquidity supportive for institutional size", trend or "Trend context available"], limit=3),
        weaknesses=as_list(["Momentum confirmation still needed", "Volatility can force staging"], limit=3),
        evidence=evidence,
        unanswered_questions=[
            "Does volume confirm the prevailing trend?",
            "Where does price sit versus the 52-week range for staging?",
        ],
        sections={
            "price_trend": trend or "Trend context assessed from recent price action",
            "momentum": src.get("momentum") or "Momentum mixed unless confirmed by breadth and volume",
            "volume": src.get("volume") or "Volume confirmation required for breakout conviction",
            "liquidity": src.get("liquidity") or "Large-cap liquidity generally supports institutional sizing",
            "range_52w": src.get("fifty_two_week") or src.get("range_52w") or "Position within the 52-week range informs entry staging",
            "volatility": src.get("volatility") or "Volatility informs position sizing and staging",
            "institutional_activity": src.get("institutional_activity") or "Watch flow signals around results",
            "technical_context": tech.get("reasoning") or src.get("technical") or "Technicals are a timing overlay, not the investment case",
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(0.45 + 0.07 * min(len(evidence), 4), default=0.48),
            "knowledge": coverage,
            "freshness": pick_confidence(leo.get("freshness_score"), default=0.6),
            "coverage": coverage,
        },
        score=float(score) if isinstance(score, (int, float)) else None,
        ctx=ctx,
    )
