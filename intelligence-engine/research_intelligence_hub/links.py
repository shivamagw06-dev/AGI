"""Soft retrieval from AGI intelligence platforms — never live providers."""

from __future__ import annotations

from typing import Any

from research_intelligence_hub.schema import (
    AnalogueLink,
    ForecastBundle,
    ForecastScenario,
    RelationshipLink,
)


def soft_market_tip() -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "CMKTP_KRIG", "inherited": False}
    try:
        from continuous_market_knowledge.production import market as cmktp_market

        pack = cmktp_market()
        if pack.get("found") and pack.get("market"):
            m = dict(pack["market"])
            tip.update(
                {
                    "inherited": True,
                    "market_regime": m.get("market_regime") or m.get("regime"),
                    "breadth": m.get("breadth"),
                    "liquidity": m.get("liquidity"),
                    "volatility": m.get("volatility"),
                    "risk_sentiment": m.get("risk_sentiment"),
                    "health_score": m.get("health_score"),
                    "leadership": m.get("leadership"),
                }
            )
    except Exception:
        pass
    return tip


def soft_relationships(sectors: list[str], macro: list[str]) -> list[RelationshipLink]:
    rows: list[RelationshipLink] = []
    try:
        from market_relationship_intelligence.production import for_indicator
        from market_relationship_intelligence.production import relationships as mkri_all

        pack = for_indicator("Repo Rate", limit=15)
        if not pack.get("n"):
            pack = mkri_all(limit=15)
        for r in pack.get("relationships") or []:
            rows.append(
                RelationshipLink(
                    source=str(r.get("source")),
                    target=str(r.get("target")),
                    relationship=str(r.get("relationship") or r.get("type") or "link"),
                    direction=str(r.get("direction") or "positive"),
                    strength=str(r.get("strength") or "Medium"),
                    confidence_pct=int(r.get("confidence_pct") or 70),
                    evidence=list(r.get("evidence") or [])[:3],
                    gateway="MKRI_KRIG",
                )
            )
    except Exception:
        pass
    if not rows:
        catalog = [
            ("RBI", "Banks", "Policy Transmission", "positive", 84),
            ("Oil", "Airlines", "Cost Shock", "negative", 80),
            ("USD", "IT Services", "Revenue Sensitivity", "positive", 82),
            ("Steel", "Auto", "Input Cost", "negative", 76),
            ("Government Capex", "Capital Goods", "Order Momentum", "positive", 85),
            ("Liquidity", "Equity Breadth", "Participation Channel", "positive", 78),
        ]
        for src, tgt, rel, direction, conf in catalog:
            if sectors or macro or True:
                rows.append(
                    RelationshipLink(
                        source=src,
                        target=tgt,
                        relationship=rel,
                        direction=direction,
                        strength="High" if conf >= 80 else "Medium",
                        confidence_pct=conf,
                        evidence=[f"Catalog relationship {src}→{tgt}"],
                        gateway="MKRI_catalog",
                    )
                )
    # Prefer relationships touching extracted sectors/macro
    keys = {s.lower() for s in sectors} | {m.lower() for m in macro}
    if keys:
        ranked = sorted(
            rows,
            key=lambda r: (
                0
                if any(k in r.source.lower() or k in r.target.lower() for k in keys)
                else 1,
                -r.confidence_pct,
            ),
        )
        return ranked[:10]
    return rows[:10]


def soft_analogues(market_hint: str = "India") -> list[AnalogueLink]:
    rows: list[AnalogueLink] = []
    try:
        from historical_market_analogue_intelligence.production import forecast_tip

        tip = forecast_tip(market=market_hint, top_k=5)
        for a in tip.get("top_analogues") or []:
            rows.append(
                AnalogueLink(
                    matched_period=str(a.get("matched_period") or "unknown"),
                    label=a.get("matched_label") or a.get("label"),
                    similarity_score=float(a.get("similarity_score") or 0),
                    matching_dimensions=list(a.get("matching_dimensions") or [])[:6],
                    historical_outcome=a.get("historical_outcome") or a.get("equity_outcome"),
                    differences=list(a.get("key_differences") or a.get("differences") or [])[:4],
                    gateway="HMKAI_KRIG",
                )
            )
    except Exception:
        pass
    if not rows:
        rows = [
            AnalogueLink(
                matched_period="2021 Liquidity Rally",
                label="Liquidity abundant",
                similarity_score=74.0,
                matching_dimensions=["liquidity", "breadth", "fii_flows"],
                historical_outcome="Equities re-rated with improving midcap participation",
                differences=["Valuation starting point higher today"],
                gateway="HMKAI_catalog",
            ),
            AnalogueLink(
                matched_period="2013 Taper Tantrum",
                label="External funding stress",
                similarity_score=68.0,
                matching_dimensions=["usd_index", "fii_flows", "volatility"],
                historical_outcome="EM risk-off; financials and high-beta underperformed",
                differences=["India FX buffers stronger vs 2013"],
                gateway="HMKAI_catalog",
            ),
            AnalogueLink(
                matched_period="2020 COVID Crash",
                label="Liquidity shock then recovery",
                similarity_score=61.0,
                matching_dimensions=["volatility", "liquidity", "market_regime"],
                historical_outcome="Sharp drawdown followed by policy-driven rebound",
                differences=["No equivalent mobility shock today"],
                gateway="HMKAI_catalog",
            ),
        ]
    return rows[:6]


def soft_forecast(*, primary_sector: str | None = None) -> ForecastBundle:
    gateways: list[str] = []
    scenarios: list[ForecastScenario] = []
    dist: dict[str, int] = {}
    confidence: dict[str, Any] = {}

    try:
        from market_forecast_intelligence.production import forecast as mkfi_forecast

        pack = mkfi_forecast(market="India", horizon="6 Months")
        if pack.get("scenarios"):
            gateways.append("MKFI_KRIG")
            dist = dict(pack.get("probability_distribution") or {})
            confidence = dict(pack.get("confidence") or {})
            for s in pack.get("scenarios") or []:
                scenarios.append(
                    ForecastScenario(
                        scenario=s.get("scenario"),
                        probability_pct=int(s.get("probability_pct") or 0),
                        confidence_pct=int(s.get("confidence_pct") or 0),
                        narrative=list(s.get("narrative") or [])[:4],
                        catalysts=list(s.get("catalysts") or [])[:4],
                        risks=list(s.get("risks") or [])[:4],
                        invalidators=list(s.get("invalidators") or [])[:4],
                    )
                )
    except Exception:
        pass

    if primary_sector:
        try:
            from sector_forecast_intelligence.production import forecast as sfi_forecast

            pack = sfi_forecast(sector=primary_sector)
            if pack.get("scenarios"):
                gateways.append("SFI_KRIG")
                if not scenarios:
                    dist = dict(pack.get("probability_distribution") or {})
                    confidence = dict(pack.get("confidence") or {})
                    for s in pack.get("scenarios") or []:
                        scenarios.append(
                            ForecastScenario(
                                scenario=s.get("scenario"),
                                probability_pct=int(s.get("probability_pct") or 0),
                                confidence_pct=int(s.get("confidence_pct") or 0),
                                narrative=list(s.get("narrative") or [])[:4],
                                catalysts=list(s.get("catalysts") or [])[:4],
                                risks=list(s.get("risks") or [])[:4],
                                invalidators=list(s.get("invalidators") or s.get("invalidation_conditions") or [])[:4],
                            )
                        )
        except Exception:
            pass

    if not scenarios:
        gateways.append("RIH_catalog_forecast")
        dist = {"Bull": 24, "Base": 52, "Bear": 24}
        confidence = {"overall_pct": 62, "label": "Medium"}
        scenarios = [
            ForecastScenario(
                scenario="Bull",
                probability_pct=24,
                confidence_pct=60,
                narrative=["Policy and liquidity support risk assets", "Breadth improves"],
                catalysts=[{"catalyst": "RBI easing", "polarity": "positive"}],
                risks=[{"risk": "Inflation re-acceleration", "severity": "High"}],
                invalidators=["Inflation exceeds forecast range"],
            ),
            ForecastScenario(
                scenario="Base",
                probability_pct=52,
                confidence_pct=66,
                narrative=["Growth stable", "Earnings meet expectations", "Moderate returns"],
                catalysts=[{"catalyst": "Earnings delivery", "polarity": "neutral"}],
                risks=[{"risk": "Range-bound leadership", "severity": "Medium"}],
                invalidators=["Material earnings miss across index heavyweights"],
            ),
            ForecastScenario(
                scenario="Bear",
                probability_pct=24,
                confidence_pct=58,
                narrative=["Global yields rise", "FII selling", "Breadth deteriorates"],
                catalysts=[{"catalyst": "Defensive rotation", "polarity": "mixed"}],
                risks=[{"risk": "Oil spike / USD strength", "severity": "High"}],
                invalidators=["Unexpected policy tightening"],
            ),
        ]

    return ForecastBundle(
        horizon="6 Months",
        scenarios=scenarios,
        probability_distribution=dist,
        confidence=confidence,
        gateways=gateways,
        predicts_single_path=False,
    )


def soft_evidence(
    *,
    companies: list[str],
    sectors: list[str],
    macro: list[str],
    sources: list[str],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = [
        {
            "kind": "research_note",
            "summary": "Source research note metadata and extracted entities",
            "refs": ["RIH_ingest"],
            "source_gateway": "RIH",
            "traceable": True,
        }
    ]
    if "CMKTP" in sources or True:
        items.append(
            {
                "kind": "market_statistics",
                "summary": "Current market regime / breadth / liquidity tip",
                "refs": ["CMKTP_KRIG"],
                "source_gateway": "CMKTP",
                "traceable": True,
            }
        )
    if companies:
        items.append(
            {
                "kind": "company_filings",
                "summary": f"Company intelligence soft-links for {', '.join(companies[:4])}",
                "refs": [f"Company:{c}" for c in companies[:4]],
                "source_gateway": "Company_Intelligence",
                "traceable": True,
            }
        )
    if sectors:
        items.append(
            {
                "kind": "sector_metrics",
                "summary": f"Sector outlook references for {', '.join(sectors[:3])}",
                "refs": [f"Sector:{s}" for s in sectors[:3]],
                "source_gateway": "Sector_Intelligence",
                "traceable": True,
            }
        )
    if macro:
        items.append(
            {
                "kind": "economic_releases",
                "summary": f"Macro topics: {', '.join(macro[:4])}",
                "refs": [f"Macro:{m}" for m in macro[:4]],
                "source_gateway": "Macro_Intelligence",
                "traceable": True,
            }
        )
    items.append(
        {
            "kind": "historical_data",
            "summary": "Historical analogues and relationship evidence attached to hub",
            "refs": ["HMKAI_KRIG", "MKRI_KRIG"],
            "source_gateway": "Historical_Intelligence",
            "traceable": True,
        }
    )
    return items


def enrich_market_links(markets: list[dict[str, Any]], tip: dict[str, Any]) -> list[dict[str, Any]]:
    if not tip.get("inherited") and not tip.get("market_regime"):
        return markets
    enriched = []
    for m in markets:
        meta = dict(m.get("meta") or {})
        meta.update(
            {
                "market_regime": tip.get("market_regime"),
                "breadth": tip.get("breadth"),
                "liquidity": tip.get("liquidity"),
                "volatility": tip.get("volatility"),
                "institutional_flows": tip.get("risk_sentiment"),
                "health_score": tip.get("health_score"),
            }
        )
        enriched.append({**m, "meta": meta, "confidence_pct": 78 if tip.get("inherited") else 60})
    return enriched
