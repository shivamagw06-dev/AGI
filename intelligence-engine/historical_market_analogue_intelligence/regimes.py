"""Historical market regime catalogs + soft builders from CMKTP / HMKIP / MKRI / HMIP."""

from __future__ import annotations

from typing import Any

from historical_market_analogue_intelligence.schema import SUPPORTED_MARKETS, MarketRegime

FEATURE_UNITS: dict[str, str] = {
    "market_regime": "0-10 ordinal",
    "breadth": "index 0-100",
    "liquidity": "index 0-100",
    "volatility": "index 0-100",
    "fii_flows": "index 0-100",
    "dii_flows": "index 0-100",
    "leadership": "index 0-100",
    "bond_yields": "%",
    "usd_index": "DXY",
    "interest_rate": "% repo",
    "inflation": "% CPI yoy",
}

MARKET_KEY_MAP: dict[str, str] = {
    "India": "india_equity",
    "Global": "global_equity",
}

# Regime ordinal: Capitulation=1 Bear=2 Correction=3 Distribution=4 Sideways=5 Recovery=7 Bull=8
MARKET_REGIME_CATALOG: dict[str, list[dict[str, Any]]] = {
    "India": [
        {
            "period": "2000",
            "label": "Dot-com Crash — breadth collapse",
            "regime_label": "Bear",
            "features": {
                "market_regime": 2.0,
                "breadth": 25.0,
                "liquidity": 30.0,
                "volatility": 85.0,
                "fii_flows": 22.0,
                "dii_flows": 40.0,
                "leadership": 30.0,
                "bond_yields": 10.5,
                "usd_index": 110.0,
                "interest_rate": 9.0,
                "inflation": 4.0,
            },
            "outcome": "Prolonged risk-off; defensives led; recovery delayed into 2003",
            "equity_outcome": "Deep underperformance then multi-year repair",
            "historical_outcome_bundle": {
                "return_30d": "Sharply negative",
                "return_90d": "Continued weakness",
                "return_180d": "Stabilisation attempt failed into 2001",
                "breadth_improvement": "Slow; participation stayed narrow",
                "sector_rotation": "Defensives / cash preferred",
                "volatility_change": "Elevated for multiple quarters",
                "leadership_change": "Tech leadership collapsed",
                "market_health_evolution": "Health index stayed depressed",
            },
            "timeline_refs": ["hmkip:india_equity:Dot-com Crash", "india:2000:Dot-com"],
            "research_refs": ["Market Research: Dot-com crash analogue"],
        },
        {
            "period": "2003",
            "label": "2003 Bull Market — credit / capex expansion",
            "regime_label": "Bull",
            "features": {
                "market_regime": 8.0,
                "breadth": 70.0,
                "liquidity": 68.0,
                "volatility": 40.0,
                "fii_flows": 65.0,
                "dii_flows": 55.0,
                "leadership": 74.0,
                "bond_yields": 6.0,
                "usd_index": 95.0,
                "interest_rate": 6.0,
                "inflation": 4.5,
            },
            "outcome": "Multi-year bull; cyclicals and banks led; breadth expanded",
            "equity_outcome": "Strong absolute and relative returns",
            "historical_outcome_bundle": {
                "return_30d": "Positive momentum continuation",
                "return_90d": "Broad risk-on",
                "return_180d": "Sustained bull leadership",
                "breadth_improvement": "Advance/decline expanded",
                "sector_rotation": "Capital Goods → Banks → Auto → Midcaps",
                "volatility_change": "Compressed",
                "leadership_change": "Cyclical leadership solidified",
                "market_health_evolution": "Health improved with liquidity",
            },
            "timeline_refs": ["hmkip:india_equity:2003 Bull Market"],
            "research_refs": ["Market Research: 2003 bull expansion"],
        },
        {
            "period": "2008",
            "label": "2008 GFC — liquidity freeze / capitulation",
            "regime_label": "Capitulation",
            "features": {
                "market_regime": 1.0,
                "breadth": 18.0,
                "liquidity": 25.0,
                "volatility": 90.0,
                "fii_flows": 15.0,
                "dii_flows": 35.0,
                "leadership": 20.0,
                "bond_yields": 8.5,
                "usd_index": 85.0,
                "interest_rate": 9.0,
                "inflation": 8.3,
            },
            "outcome": "Global liquidity freeze; policy response; delayed recovery into 2009",
            "equity_outcome": "Deep drawdown then V-shaped policy-led rebound",
            "historical_outcome_bundle": {
                "return_30d": "Severe drawdown",
                "return_90d": "Capitulation then bounce",
                "return_180d": "Policy liquidity supported recovery",
                "breadth_improvement": "Collapsed then snapped back",
                "sector_rotation": "Defensives then cyclicals on recovery",
                "volatility_change": "Spike then gradual compression",
                "leadership_change": "Quality large-caps first",
                "market_health_evolution": "Health collapsed then repaired",
            },
            "timeline_refs": ["hmkip:india_equity:2008 GFC", "hmkip:volatility:GFC vol spike"],
            "research_refs": ["Market Research: GFC liquidity freeze"],
        },
        {
            "period": "2013",
            "label": "2013 Taper Tantrum — FII outflow / INR stress",
            "regime_label": "Correction",
            "features": {
                "market_regime": 3.0,
                "breadth": 40.0,
                "liquidity": 45.0,
                "volatility": 62.0,
                "fii_flows": 35.0,
                "dii_flows": 50.0,
                "leadership": 44.0,
                "bond_yields": 8.8,
                "usd_index": 82.0,
                "interest_rate": 7.75,
                "inflation": 9.5,
            },
            "outcome": "EM risk-off; FII selling; large-caps relatively resilient",
            "equity_outcome": "Correction with selective quality outperformance",
            "historical_outcome_bundle": {
                "return_30d": "Negative with USD strength",
                "return_90d": "Stabilisation after policy response",
                "return_180d": "Gradual repair as INR stabilised",
                "breadth_improvement": "Narrow; mid/small lagged",
                "sector_rotation": "Large-cap financials preference",
                "volatility_change": "Elevated then moderated",
                "leadership_change": "Quality over beta",
                "market_health_evolution": "Health soft until flows returned",
            },
            "timeline_refs": [
                "hmkip:india_equity:2013 Taper Tantrum",
                "hmkip:institutional_flows:FII taper episode",
            ],
            "research_refs": ["Market Research: 2013 taper / FII stress"],
        },
        {
            "period": "2016",
            "label": "2016 Demonetisation — liquidity shock",
            "regime_label": "Correction",
            "features": {
                "market_regime": 3.0,
                "breadth": 46.0,
                "liquidity": 50.0,
                "volatility": 58.0,
                "fii_flows": 42.0,
                "dii_flows": 55.0,
                "leadership": 50.0,
                "bond_yields": 6.8,
                "usd_index": 100.0,
                "interest_rate": 6.25,
                "inflation": 4.5,
            },
            "outcome": "Cash/liquidity disruption; mid/small stress; eventual recovery",
            "equity_outcome": "Short correction; domestic flows cushioned",
            "historical_outcome_bundle": {
                "return_30d": "Soft to negative",
                "return_90d": "Stabilisation",
                "return_180d": "Recovery with policy normalisation",
                "breadth_improvement": "Dip then repair",
                "sector_rotation": "Cash-heavy / staples relative strength",
                "volatility_change": "Temporary spike",
                "leadership_change": "Large-caps preferred",
                "market_health_evolution": "Temporary dip then repair",
            },
            "timeline_refs": ["hmkip:india_equity:2016 Demonetisation"],
            "research_refs": ["Market Research: Demonetisation liquidity shock"],
        },
        {
            "period": "2020",
            "label": "2020 COVID Crash — breadth/liquidity collapse",
            "regime_label": "Capitulation",
            "features": {
                "market_regime": 1.0,
                "breadth": 15.0,
                "liquidity": 22.0,
                "volatility": 92.0,
                "fii_flows": 18.0,
                "dii_flows": 48.0,
                "leadership": 18.0,
                "bond_yields": 6.2,
                "usd_index": 102.0,
                "interest_rate": 4.0,
                "inflation": 6.2,
            },
            "outcome": "Historic V-recovery after policy liquidity injection",
            "equity_outcome": "Crash then liquidity rally; IT/Pharma led early",
            "historical_outcome_bundle": {
                "return_30d": "Severe drawdown",
                "return_90d": "Sharp rebound on liquidity",
                "return_180d": "Broad recovery into 2021",
                "breadth_improvement": "Collapsed then snapped back",
                "sector_rotation": "Defensives → Growth / IT → Cyclicals",
                "volatility_change": "Spike then compression",
                "leadership_change": "IT / Pharma then broader risk",
                "market_health_evolution": "Health collapsed then rapidly repaired",
            },
            "timeline_refs": [
                "hmkip:india_equity:2020 COVID Crash",
                "hmkip:volatility:COVID vol spike",
                "hmkip:institutional_flows:COVID FII selling",
            ],
            "research_refs": ["Market Research: COVID crash / liquidity recovery"],
        },
        {
            "period": "2021",
            "label": "2021 Recovery — liquidity abundant / breadth strong",
            "regime_label": "Recovery",
            "features": {
                "market_regime": 7.0,
                "breadth": 72.0,
                "liquidity": 78.0,
                "volatility": 38.0,
                "fii_flows": 70.0,
                "dii_flows": 65.0,
                "leadership": 76.0,
                "bond_yields": 6.1,
                "usd_index": 93.0,
                "interest_rate": 4.0,
                "inflation": 5.5,
            },
            "outcome": "Liquidity rally; mid/small catch-up; leadership broadened",
            "equity_outcome": "Strong absolute returns; elevated valuations",
            "historical_outcome_bundle": {
                "return_30d": "Positive",
                "return_90d": "Continued risk-on",
                "return_180d": "Sustained recovery leadership",
                "breadth_improvement": "Strong equal-weight participation",
                "sector_rotation": "Large → Mid → Small",
                "volatility_change": "Compressed",
                "leadership_change": "Growth / discretionary leadership",
                "market_health_evolution": "Health elevated with liquidity",
            },
            "timeline_refs": ["hmkip:india_equity:2021 Recovery", "hmkip:liquidity"],
            "research_refs": ["Market Research: 2021 liquidity recovery"],
        },
        {
            "period": "2022",
            "label": "2022 Inflation Shock — distribution / yield pressure",
            "regime_label": "Distribution",
            "features": {
                "market_regime": 4.0,
                "breadth": 48.0,
                "liquidity": 52.0,
                "volatility": 68.0,
                "fii_flows": 40.0,
                "dii_flows": 58.0,
                "leadership": 55.0,
                "bond_yields": 7.4,
                "usd_index": 112.0,
                "interest_rate": 6.25,
                "inflation": 6.7,
            },
            "outcome": "Multiple compression; Energy/Banks led; growth lagged",
            "equity_outcome": "Range-bound with style rotation to value/financials",
            "historical_outcome_bundle": {
                "return_30d": "Mixed to soft",
                "return_90d": "Style rotation dominant",
                "return_180d": "Stabilisation with elevated yields",
                "breadth_improvement": "Uneven; midcaps lagged early",
                "sector_rotation": "Energy / Banks / Commodities leadership",
                "volatility_change": "Elevated then moderated",
                "leadership_change": "Value / financials over growth",
                "market_health_evolution": "Health mixed under yield pressure",
            },
            "timeline_refs": [
                "hmkip:india_equity:2022 Inflation Shock",
                "hmkip:cross_asset",
            ],
            "research_refs": ["Market Research: 2022 inflation / distribution"],
        },
        {
            "period": "2025",
            "label": "Post-inflation consolidation — DII cushion / moderate vol",
            "regime_label": "Sideways",
            "features": {
                "market_regime": 5.0,
                "breadth": 58.0,
                "liquidity": 64.0,
                "volatility": 45.0,
                "fii_flows": 55.0,
                "dii_flows": 68.0,
                "leadership": 62.0,
                "bond_yields": 6.9,
                "usd_index": 104.0,
                "interest_rate": 6.5,
                "inflation": 3.7,
            },
            "outcome": "Range-bound with domestic flow support; selective leadership",
            "equity_outcome": "Constructive but selective; valuation discipline",
            "historical_outcome_bundle": {
                "return_30d": "Mixed / range-bound",
                "return_90d": "Selective risk-on on dips",
                "return_180d": "Domestic cushion supports floor",
                "breadth_improvement": "Moderate",
                "sector_rotation": "Quality / domestic cyclicals",
                "volatility_change": "Compressed vs 2022",
                "leadership_change": "Diversified with DII preference",
                "market_health_evolution": "Stable-to-improving",
            },
            "timeline_refs": [
                "hmkip:india_equity:Post-inflation consolidation",
                "hmkip:institutional_flows:DII cushion era",
            ],
            "research_refs": ["Market Research: DII cushion consolidation"],
        },
    ],
    "Global": [
        {
            "period": "2008",
            "label": "Global GFC",
            "regime_label": "Capitulation",
            "features": {
                "market_regime": 1.0,
                "breadth": 16.0,
                "liquidity": 20.0,
                "volatility": 88.0,
                "fii_flows": 14.0,
                "dii_flows": 30.0,
                "leadership": 18.0,
                "bond_yields": 3.5,
                "usd_index": 85.0,
                "interest_rate": 1.0,
                "inflation": 2.0,
            },
            "outcome": "Global risk-off then coordinated policy response",
            "equity_outcome": "Deep drawdown then recovery",
            "historical_outcome_bundle": {
                "return_30d": "Severe negative",
                "return_90d": "Capitulation bounce",
                "return_180d": "Policy-led repair",
                "breadth_improvement": "Collapsed then repaired",
                "sector_rotation": "Defensives then cyclicals",
                "volatility_change": "Spike then compression",
                "leadership_change": "Quality large-caps",
                "market_health_evolution": "Collapsed then repaired",
            },
            "timeline_refs": ["hmkip:global_equity:Global GFC"],
            "research_refs": ["Market Research: Global GFC"],
        },
        {
            "period": "2020",
            "label": "Global COVID Crash",
            "regime_label": "Capitulation",
            "features": {
                "market_regime": 1.0,
                "breadth": 20.0,
                "liquidity": 24.0,
                "volatility": 90.0,
                "fii_flows": 20.0,
                "dii_flows": 40.0,
                "leadership": 22.0,
                "bond_yields": 0.8,
                "usd_index": 102.0,
                "interest_rate": 0.25,
                "inflation": 1.5,
            },
            "outcome": "Global V-recovery on unprecedented liquidity",
            "equity_outcome": "Crash then tech/growth leadership",
            "historical_outcome_bundle": {
                "return_30d": "Severe drawdown",
                "return_90d": "Sharp rebound",
                "return_180d": "Liquidity rally",
                "breadth_improvement": "Snap-back",
                "sector_rotation": "Growth / tech leadership",
                "volatility_change": "Spike then compression",
                "leadership_change": "Mega-cap growth",
                "market_health_evolution": "Rapid repair",
            },
            "timeline_refs": ["hmkip:global_equity:Global COVID Crash"],
            "research_refs": ["Market Research: Global COVID"],
        },
        {
            "period": "2022",
            "label": "Global Inflation Shock",
            "regime_label": "Distribution",
            "features": {
                "market_regime": 4.0,
                "breadth": 45.0,
                "liquidity": 50.0,
                "volatility": 65.0,
                "fii_flows": 42.0,
                "dii_flows": 48.0,
                "leadership": 50.0,
                "bond_yields": 4.0,
                "usd_index": 112.0,
                "interest_rate": 4.5,
                "inflation": 8.0,
            },
            "outcome": "Multiple compression; USD strength; value over growth",
            "equity_outcome": "Style rotation; EM pressure",
            "historical_outcome_bundle": {
                "return_30d": "Soft",
                "return_90d": "Style rotation",
                "return_180d": "Stabilisation with high yields",
                "breadth_improvement": "Uneven",
                "sector_rotation": "Energy / value leadership",
                "volatility_change": "Elevated",
                "leadership_change": "Value over growth",
                "market_health_evolution": "Mixed",
            },
            "timeline_refs": ["hmkip:global_equity:Global Inflation Shock"],
            "research_refs": ["Market Research: Global inflation shock"],
        },
        {
            "period": "2025",
            "label": "Post-shock normalisation",
            "regime_label": "Sideways",
            "features": {
                "market_regime": 5.0,
                "breadth": 58.0,
                "liquidity": 62.0,
                "volatility": 42.0,
                "fii_flows": 56.0,
                "dii_flows": 55.0,
                "leadership": 60.0,
                "bond_yields": 3.8,
                "usd_index": 104.0,
                "interest_rate": 4.0,
                "inflation": 2.8,
            },
            "outcome": "Normalisation; selective risk-on",
            "equity_outcome": "Constructive but selective",
            "historical_outcome_bundle": {
                "return_30d": "Mixed",
                "return_90d": "Selective risk-on",
                "return_180d": "Gradual normalisation",
                "breadth_improvement": "Moderate",
                "sector_rotation": "Diversified",
                "volatility_change": "Compressed",
                "leadership_change": "Quality bias",
                "market_health_evolution": "Stable",
            },
            "timeline_refs": ["hmkip:global_equity:Post-shock normalisation"],
            "research_refs": ["Market Research: Global normalisation"],
        },
    ],
}

CURRENT_REGIME_TIPS: dict[str, dict[str, Any]] = {
    "India": {
        "period": "2026",
        "label": "Current — post-inflation consolidation, DII cushion, moderate vol",
        "regime_label": "Sideways",
        "features": {
            "market_regime": 5.2,
            "breadth": 58.0,
            "liquidity": 64.0,
            "volatility": 45.0,
            "fii_flows": 56.0,
            "dii_flows": 68.0,
            "leadership": 63.0,
            "bond_yields": 6.85,
            "usd_index": 103.5,
            "interest_rate": 6.25,
            "inflation": 3.9,
        },
    },
    "Global": {
        "period": "2026",
        "label": "Current — soft-landing optionality, moderate USD",
        "regime_label": "Sideways",
        "features": {
            "market_regime": 5.5,
            "breadth": 60.0,
            "liquidity": 63.0,
            "volatility": 42.0,
            "fii_flows": 58.0,
            "dii_flows": 54.0,
            "leadership": 61.0,
            "bond_yields": 3.9,
            "usd_index": 103.0,
            "interest_rate": 4.0,
            "inflation": 2.7,
        },
    },
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
        "us": "Global",
        "spx": "Global",
    }
    key = raw.lower().replace("-", "_").replace(" ", "_")
    return aliases.get(key)


def catalog_regimes(*, market: str) -> list[MarketRegime]:
    market_n = normalize_market(market) or market
    rows = MARKET_REGIME_CATALOG.get(market_n) or []
    out: list[MarketRegime] = []
    for row in rows:
        out.append(
            MarketRegime(
                market=market_n,
                market_key=MARKET_KEY_MAP.get(market_n),
                country="India" if market_n == "India" else "Global",
                period=str(row["period"]),
                label=str(row["label"]),
                regime_label=row.get("regime_label"),
                features=dict(row["features"]),
                feature_units=dict(FEATURE_UNITS),
                outcome=row.get("outcome"),
                equity_outcome=row.get("equity_outcome"),
                historical_outcome_bundle=dict(row.get("historical_outcome_bundle") or {}),
                timeline_refs=list(row.get("timeline_refs") or []),
                research_refs=list(row.get("research_refs") or []),
                source_layers=["hmkai_regime_catalog"],
                provenance={
                    "kind": "institutional_catalog",
                    "aligned_with": "HMKIP_seeded_series",
                },
            )
        )
    return out


def build_historical_regimes(
    *,
    market: str,
    enrich_hmkip: bool = True,
) -> list[MarketRegime]:
    regimes = catalog_regimes(market=market)
    if enrich_hmkip:
        regimes = [enrich_regime_from_hmkip(r) for r in regimes]
    return regimes


def build_current_regime(*, market: str, enrich_cmktp: bool = True) -> MarketRegime:
    market_n = normalize_market(market) or market
    tip = CURRENT_REGIME_TIPS.get(market_n) or CURRENT_REGIME_TIPS["India"]
    features = dict(tip["features"])
    layers = ["hmkai_current_tip"]
    provenance: dict[str, Any] = {"kind": "current_tip"}

    if enrich_cmktp:
        overlay = soft_cmktp_current_features(market_n)
        if overlay:
            features = {**features, **overlay}
            layers.append("CMKTP")
            provenance["cmktp_overlay_keys"] = sorted(overlay.keys())

    macro = soft_hmip_macro_features()
    if macro:
        for k, v in macro.items():
            if v is not None:
                features[k] = v
        layers.append("HMIP")
        provenance["hmip_overlay_keys"] = sorted(macro.keys())

    return MarketRegime(
        market=market_n,
        market_key=MARKET_KEY_MAP.get(market_n),
        country="India" if market_n == "India" else "Global",
        period=str(tip["period"]),
        label=str(tip["label"]),
        regime_label=str(tip.get("regime_label") or "Sideways"),
        features=features,
        feature_units=dict(FEATURE_UNITS),
        outcome="Current observation window — outcomes deferred to Forecast Intelligence",
        equity_outcome=None,
        timeline_refs=[f"cmktp:{MARKET_KEY_MAP.get(market_n, market_n)}:latest"],
        research_refs=[f"Market Research: current {market_n}"],
        source_layers=layers,
        provenance=provenance,
    )


def soft_cmktp_current_features(market: str) -> dict[str, float]:
    """Map published CMKTP tips into dimension features — never collects."""
    try:
        from continuous_market_knowledge.production import market as cmktp_market
    except Exception:
        return {}
    try:
        pack = cmktp_market()
    except Exception:
        return {}
    if not pack.get("found"):
        return {}
    m = pack.get("market") or {}
    out: dict[str, float] = {}
    regime = str(m.get("market_regime") or m.get("regime") or "").lower()
    mapping = {
        "capitulation": 1.0,
        "bear": 2.0,
        "correction": 3.0,
        "distribution": 4.0,
        "sideways": 5.0,
        "recovery": 7.0,
        "bull": 8.0,
        "expansion": 8.0,
    }
    for key, val in mapping.items():
        if key in regime:
            out["market_regime"] = val
            break
    health = m.get("health_score")
    if health is not None:
        try:
            h = float(health)
            out["breadth"] = h
            out["liquidity"] = min(100.0, h + 4.0)
            out["leadership"] = h
        except (TypeError, ValueError):
            pass
    sentiment = str(m.get("risk_sentiment") or "").lower()
    if "off" in sentiment:
        out["volatility"] = 70.0
        out["fii_flows"] = 35.0
    elif "on" in sentiment:
        out["volatility"] = 40.0
        out["fii_flows"] = 65.0
    return out


def enrich_regime_from_hmkip(regime: MarketRegime) -> MarketRegime:
    """Soft-confirm via HMKIP timeline completeness — never collects."""
    try:
        from historical_market_intelligence.production import market as hmkip_market
    except Exception:
        return regime

    key = regime.market_key or MARKET_KEY_MAP.get(regime.market)
    if not key:
        return regime
    try:
        tip = hmkip_market(key, limit=20)
    except Exception:
        return regime
    if not tip.get("found"):
        return regime

    tl = tip.get("timeline") or {}
    refs = list(regime.timeline_refs)
    refs.append(f"hmkip:{key}:timeline")
    layers = list(regime.source_layers or [])
    if "HMKIP" not in layers:
        layers.append("HMKIP")
    regime.timeline_refs = refs
    regime.source_layers = layers
    regime.provenance = {
        **(regime.provenance or {}),
        "hmkip_soft_confirmed": True,
        "hmkip_completeness_pct": tl.get("completeness_pct"),
        "providers_queried": [],
    }
    return regime


def soft_hmip_macro_features() -> dict[str, float]:
    """Soft macro overlays for interest / inflation — never collects."""
    out: dict[str, float] = {}
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator
    except Exception:
        return out

    mapping = {
        "Repo Rate": "interest_rate",
        "CPI": "inflation",
    }
    for ind, dim in mapping.items():
        try:
            tip = hmip_indicator(ind, country="India")
        except Exception:
            continue
        if not tip.get("found"):
            continue
        obs = tip.get("observations") or tip.get("latest") or []
        val = None
        if isinstance(obs, dict):
            val = obs.get("value")
        elif isinstance(obs, list) and obs:
            val = (obs[-1] or {}).get("value")
        timeline = tip.get("timeline") or {}
        if val is None and timeline.get("latest_value") is not None:
            val = timeline.get("latest_value")
        try:
            if val is not None:
                out[dim] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def soft_mkri_relationships(market: str = "India") -> list[dict[str, Any]]:
    """Soft tip from MKRI for explainability — never rebuilds graph."""
    try:
        from market_relationship_intelligence.production import for_indicator
        from market_relationship_intelligence.production import relationships as mkri_all
    except Exception:
        return []
    try:
        pack = for_indicator("Repo Rate", limit=10)
        if not pack.get("n"):
            pack = mkri_all(limit=10)
    except Exception:
        return []
    rows = []
    for r in pack.get("relationships") or []:
        rows.append(
            {
                "source": r.get("source"),
                "target": r.get("target"),
                "relationship": r.get("relationship"),
                "direction": r.get("direction"),
                "confidence_pct": r.get("confidence_pct"),
                "kind": r.get("kind"),
                "average_lag": r.get("average_lag"),
                "gateway": "MKRI_KRIG",
            }
        )
    return rows


def supported_markets() -> list[str]:
    return list(SUPPORTED_MARKETS)
