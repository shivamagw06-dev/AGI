"""Assemble Market Forecast Bundle from Phase 12 + Macro/Sector AGI-owned knowledge only."""

from __future__ import annotations

from typing import Any

from market_forecast_intelligence import traces
from market_forecast_intelligence.schema import SUPPORTED_MARKETS, MarketForecastBundle

MARKET_KEY_MAP: dict[str, str] = {
    "India": "india_equity",
    "Global": "global_equity",
}


def normalize_market(name: str | None) -> str | None:
    if not name:
        return None
    raw = str(name).strip()
    for s in SUPPORTED_MARKETS:
        if raw.lower() == s.lower():
            return s
    aliases = {
        "india": "India",
        "india_equity": "India",
        "nifty": "India",
        "sensex": "India",
        "in": "India",
        "global": "Global",
        "global_equity": "Global",
        "world": "Global",
    }
    key = raw.lower().replace("-", "_").replace(" ", "_")
    return aliases.get(key)


def soft_current_market(market: str) -> dict[str, Any]:
    out: dict[str, Any] = {"market": market, "gateway": "CMKTP_KRIG", "providers_queried": []}
    try:
        from continuous_market_knowledge.production import market as cmktp_market

        pack = cmktp_market()
        if pack.get("found") and pack.get("market"):
            latest = dict(pack["market"])
            out["available"] = True
            out["market_regime"] = latest.get("market_regime") or latest.get("regime")
            out["risk_sentiment"] = latest.get("risk_sentiment")
            out["health_score"] = latest.get("health_score")
            out["breadth"] = latest.get("breadth")
            out["leadership"] = latest.get("leadership")
            out["latest"] = latest
            return out
    except Exception:
        pass
    out["available"] = False
    return out


def soft_historical(market: str) -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "HMKIP_KRIG", "providers_queried": []}
    try:
        from historical_market_intelligence.production import market as hmkip_market

        key = MARKET_KEY_MAP.get(market) or "india_equity"
        pack = hmkip_market(key, limit=40)
        if pack.get("found"):
            tip["available"] = True
            tip["n"] = pack.get("n")
            tip["timeline"] = pack.get("timeline")
            tip["completeness_pct"] = (pack.get("timeline") or {}).get("completeness_pct")
            return tip
    except Exception:
        pass
    tip["available"] = False
    return tip


def soft_analogues(market: str) -> list[dict[str, Any]]:
    try:
        from historical_market_analogue_intelligence.production import forecast_tip

        tip = forecast_tip(market=market, top_k=5)
        return list(tip.get("top_analogues") or [])
    except Exception:
        return []


def soft_regime(market: str) -> dict[str, Any]:
    try:
        from historical_market_analogue_intelligence.production import current_regime

        pack = current_regime(market=market)
        return pack.get("regime") or {}
    except Exception:
        return {}


def soft_relationships(market: str) -> list[dict[str, Any]]:
    try:
        from market_relationship_intelligence.production import for_indicator
        from market_relationship_intelligence.production import relationships as mkri_all

        pack = for_indicator("Repo Rate", limit=20)
        if not pack.get("n"):
            pack = mkri_all(limit=20)
        return list(pack.get("relationships") or [])
    except Exception:
        return []


def soft_macro_forecast() -> dict[str, Any]:
    """Inherit macro assumptions from Macro MFI — never invent a parallel macro view."""
    tip: dict[str, Any] = {"gateway": "MFI_KRIG", "providers_queried": [], "inherited": False}
    try:
        from macroeconomic_forecast_intelligence.production import forecast as mfi_forecast
        from macroeconomic_forecast_intelligence.production import probability as mfi_probability

        pack = mfi_forecast(country="India", region="India")
        prob = mfi_probability(country="India")
        tip["inherited"] = True
        tip["probability_distribution"] = pack.get("probability_distribution") or prob.get(
            "distribution"
        )
        tip["confidence"] = pack.get("confidence") or prob.get("confidence")
        tip["current_regime"] = pack.get("current_regime")
        scenarios = []
        for s in pack.get("scenarios") or []:
            scenarios.append(
                {
                    "scenario": s.get("scenario"),
                    "probability_pct": s.get("probability_pct"),
                    "repo_rate": s.get("repo_rate"),
                    "inflation": s.get("inflation"),
                    "gdp": s.get("gdp"),
                    "usdinr": s.get("usdinr"),
                }
            )
        tip["scenarios"] = scenarios
        tip["available"] = bool(tip["probability_distribution"] or scenarios)
    except Exception:
        tip["available"] = False
    return tip


def soft_sector_forecast() -> dict[str, Any]:
    """Soft tip from SFI for leadership / rotation inheritance."""
    tip: dict[str, Any] = {"gateway": "SFI_KRIG", "providers_queried": [], "inherited": False}
    try:
        from sector_forecast_intelligence.production import forecast as sfi_forecast
        from sector_forecast_intelligence.production import forecast_all

        pack = sfi_forecast(sector="Banking")
        tip["inherited"] = True
        tip["probability_distribution"] = pack.get("probability_distribution")
        tip["confidence"] = pack.get("confidence")
        tip["sample_sector"] = "Banking"
        tip["sample_leadership"] = [
            s.get("scenario") for s in (pack.get("scenarios") or [])[:3]
        ]
        all_pack = forecast_all(limit=6)
        tip["sector_summaries"] = all_pack.get("forecasts") or []
        tip["available"] = bool(tip["probability_distribution"])
    except Exception:
        tip["available"] = False
    return tip


def soft_research(market: str) -> dict[str, Any]:
    return {
        "market_research_office": {
            "market": market,
            "stance": f"Evidence-linked {market} market outlook from AGI market stack",
            "themes": [
                "Regime",
                "Breadth",
                "Liquidity",
                "Flows",
                "Leadership",
                "Cross-asset",
            ],
        },
        "policy_research": ["RBI / fiscal / liquidity watch"],
        "gateway": "Market_Research_Tip",
        "providers_queried": [],
    }


def soft_monitoring(market: str) -> list[dict[str, Any]]:
    return [
        {"event": "RBI MPC / policy path", "status": "Scheduled", "importance": "Critical"},
        {"event": "FII / DII flow digest", "status": "Watching", "importance": "High"},
        {"event": f"{market} breadth / liquidity monitor", "status": "Watching", "importance": "High"},
        {"event": "Global yields / USD transmission", "status": "Watching", "importance": "High"},
        {"event": "Earnings season / index heavyweights", "status": "Watching", "importance": "Medium"},
    ]


def _completeness(
    *,
    current: dict[str, Any],
    hist: dict[str, Any],
    analogues: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    macro: dict[str, Any],
    sector: dict[str, Any],
    research: dict[str, Any],
    monitoring: list[dict[str, Any]],
) -> int:
    score = 0
    if current.get("available"):
        score += 18
    if hist.get("available"):
        score += 12
    if analogues:
        score += 15
    if relationships:
        score += 12
    if macro.get("available") or macro.get("inherited"):
        score += 15
    if sector.get("available") or sector.get("inherited"):
        score += 10
    if research:
        score += 10
    if monitoring:
        score += 8
    return min(100, score)


def assemble_bundle(
    *,
    market: str,
    horizon: str = "6 Months",
    country: str | None = None,
) -> MarketForecastBundle:
    mkt = normalize_market(market) or market
    country_n = country or ("India" if mkt == "India" else "Global")
    span = traces.begin(
        "market_forecast_bundle",
        meta={"market": mkt, "horizon": horizon, "country": country_n},
    )
    sources: list[str] = []

    current = soft_current_market(mkt)
    if current.get("available"):
        sources.append("CMKTP")
    hist = soft_historical(mkt)
    if hist.get("available"):
        sources.append("HMKIP")
    analogues = soft_analogues(mkt)
    if analogues:
        sources.append("HMKAI")
    regime = soft_regime(mkt)
    relationships = soft_relationships(mkt)
    if relationships:
        sources.append("MKRI")
    macro = soft_macro_forecast()
    if macro.get("available") or macro.get("inherited"):
        sources.append("MFI")
    sector = soft_sector_forecast()
    if sector.get("available") or sector.get("inherited"):
        sources.append("SFI")
    research = soft_research(mkt)
    sources.append("Market_Research_Tip")
    monitoring = soft_monitoring(mkt)

    completeness = _completeness(
        current=current,
        hist=hist,
        analogues=analogues,
        relationships=relationships,
        macro=macro,
        sector=sector,
        research=research,
        monitoring=monitoring,
    )
    bundle = MarketForecastBundle(
        market=mkt,
        country=country_n,
        horizon=horizon,
        current_market=current,
        current_regime=regime,
        historical_tip=hist,
        analogues=analogues,
        relationships=relationships,
        macro_forecast_tip=macro,
        sector_forecast_tip=sector,
        research=research,
        monitoring=monitoring,
        completeness_pct=completeness,
        sources=sources,
        providers_queried=[],
    )
    traces.end(
        span,
        output={
            "market": mkt,
            "horizon": horizon,
            "completeness_pct": completeness,
            "sources": sources,
            "analogue_n": len(analogues),
            "relationship_n": len(relationships),
        },
    )
    return bundle
