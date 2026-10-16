"""Historical macro regime catalog + builders from CMKP / HMIP soft tips."""

from __future__ import annotations

from typing import Any

from historical_macro_analogue_intelligence.schema import MacroRegime

# Evidence-backed India macro regime vectors. Numeric tips align with HMIP seeded
# series where available; bond/currency/commodity fill institutional research gaps
# until those series are ingested into HMIP.

HISTORICAL_REGIME_CATALOG: list[dict[str, Any]] = [
    {
        "period": "2008",
        "label": "GFC — policy spike + growth collapse",
        "features": {
            "interest_rate": 9.00,
            "inflation": 8.3,
            "gdp": 3.1,
            "liquidity": -1.5,
            "fiscal": 6.0,
            "currency": 48.0,
            "bond_yield": 8.0,
            "global_growth": 3.0,
            "commodity": 9.5,
        },
        "outcome": "Emergency easing followed; credit and growth contracted",
        "equity_outcome": "Indian equities sold off sharply; multi-quarter recovery after policy response",
        "timeline_refs": ["india:2008:GFC", "india:rbi_rate_cycle"],
        "research_refs": ["Macro Research: GFC transmission India"],
    },
    {
        "period": "2013",
        "label": "Taper tantrum — high CPI + INR stress",
        "features": {
            "interest_rate": 7.75,
            "inflation": 9.5,
            "gdp": 5.5,
            "liquidity": -0.5,
            "fiscal": 4.5,
            "currency": 68.0,
            "bond_yield": 8.5,
            "global_growth": 3.4,
            "commodity": 6.0,
        },
        "outcome": "RBI defense of INR; subsequent disinflation path into MPC framework",
        "equity_outcome": "INR-sensitive and rate-sensitive sectors under pressure; gradual normalisation",
        "timeline_refs": ["india:2013:Taper Tantrum", "india:rbi_rate_cycle"],
        "research_refs": ["Macro Research: 2013 external vulnerability"],
    },
    {
        "period": "2018",
        "label": "Late-cycle moderate inflation / consolidating fiscal",
        "features": {
            "interest_rate": 6.50,
            "inflation": 3.4,
            "gdp": 6.5,
            "liquidity": 0.8,
            "fiscal": 3.4,
            "currency": 70.0,
            "bond_yield": 7.7,
            "global_growth": 3.6,
            "commodity": 4.3,
        },
        "outcome": "Stable growth-inflation mix; NBFC stress later in cycle",
        "equity_outcome": "Broad markets constructive until late-2018 financial-sector shock",
        "timeline_refs": ["india:2018:Late Cycle", "india:rbi_rate_cycle"],
        "research_refs": ["Macro Research: 2018 growth-inflation balance"],
    },
    {
        "period": "2020",
        "label": "COVID policy response — emergency easing",
        "features": {
            "interest_rate": 4.00,
            "inflation": 6.2,
            "gdp": -5.8,
            "liquidity": 3.5,
            "fiscal": 9.2,
            "currency": 76.0,
            "bond_yield": 5.9,
            "global_growth": -2.8,
            "commodity": 1.2,
        },
        "outcome": "Liquidity surge; fiscal expansion; V-shaped growth rebound into 2021",
        "equity_outcome": "Sharp crash then liquidity-driven rally; breadth recovered with reopening",
        "timeline_refs": ["india:2020:COVID Policy Response", "india:rbi_rate_cycle"],
        "research_refs": ["Macro Research: COVID liquidity measures"],
    },
    {
        "period": "2022",
        "label": "Inflation shock — RBI tightening cycle",
        "features": {
            "interest_rate": 6.25,
            "inflation": 6.7,
            "gdp": 7.0,
            "liquidity": -0.8,
            "fiscal": 6.4,
            "currency": 82.0,
            "bond_yield": 7.4,
            "global_growth": 3.4,
            "commodity": 13.7,
        },
        "outcome": "Aggressive repo hiking; WPI spike; NIM support for banks",
        "equity_outcome": "Growth assets pressured; financials relatively resilient on NIM",
        "timeline_refs": ["india:2022:Inflation Cycle", "india:rbi_rate_cycle"],
        "research_refs": ["Macro Research: 2022 inflation / tightening"],
    },
    {
        "period": "2025",
        "label": "Disinflation with elevated-but-stable repo",
        "features": {
            "interest_rate": 6.50,
            "inflation": 3.7,
            "gdp": 7.4,
            "liquidity": 1.2,
            "fiscal": 5.1,
            "currency": 83.5,
            "bond_yield": 6.9,
            "global_growth": 3.2,
            "commodity": 2.1,
        },
        "outcome": "Growth resilient; inflation near target; policy hold bias",
        "equity_outcome": "Domestic cyclicals and financials supported by growth/liquidity mix",
        "timeline_refs": ["india:2025:Rate-Cut Optionality", "india:rbi_rate_cycle"],
        "research_refs": ["Macro Research: 2025 disinflation window"],
    },
]

FEATURE_UNITS: dict[str, str] = {
    "interest_rate": "% repo",
    "inflation": "% CPI yoy",
    "gdp": "% GDP yoy",
    "liquidity": "INR lakh crore surplus",
    "fiscal": "% of GDP deficit",
    "currency": "USDINR",
    "bond_yield": "% G-Sec 10Y",
    "global_growth": "% WEO",
    "commodity": "% WPI yoy",
}

# Map HMIP / CMKP indicator names → similarity dimension keys
INDICATOR_TO_DIMENSION: dict[str, str] = {
    "Repo Rate": "interest_rate",
    "CPI": "inflation",
    "Core Inflation": "inflation",
    "GDP": "gdp",
    "GVA": "gdp",
    "IIP": "gdp",
    "Banking Liquidity": "liquidity",
    "Credit Growth": "liquidity",
    "Fiscal Deficit": "fiscal",
    "Forex Reserves": "currency",  # reserves tip; USDINR preferred when present
    "USDINR": "currency",
    "G-Sec 10Y": "bond_yield",
    "WEO Global Growth": "global_growth",
    "World Bank Global Growth": "global_growth",
    "WPI": "commodity",
    "Crude Oil": "commodity",
}


def catalog_regimes(*, country: str = "India") -> list[MacroRegime]:
    out: list[MacroRegime] = []
    for row in HISTORICAL_REGIME_CATALOG:
        out.append(
            MacroRegime(
                country=country,
                period=str(row["period"]),
                label=str(row["label"]),
                features=dict(row["features"]),
                feature_units=dict(FEATURE_UNITS),
                outcome=row.get("outcome"),
                equity_outcome=row.get("equity_outcome"),
                timeline_refs=list(row.get("timeline_refs") or []),
                research_refs=list(row.get("research_refs") or []),
                source_layers=["hmai_regime_catalog"],
                provenance={"kind": "institutional_catalog", "aligned_with": "HMIP_seeded_series"},
            )
        )
    return out


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def features_from_indicator_tips(tips: dict[str, float | None]) -> dict[str, float]:
    """Collapse indicator tips into dimension features (first non-null wins per dim)."""
    features: dict[str, float] = {}
    # Prefer more specific indicators when both present
    priority = [
        "Repo Rate",
        "CPI",
        "GDP",
        "Banking Liquidity",
        "Fiscal Deficit",
        "USDINR",
        "Forex Reserves",
        "G-Sec 10Y",
        "WEO Global Growth",
        "WPI",
        "Crude Oil",
        "Credit Growth",
        "GVA",
        "IIP",
        "Core Inflation",
        "World Bank Global Growth",
    ]
    for ind in priority:
        dim = INDICATOR_TO_DIMENSION.get(ind)
        if not dim or dim in features:
            continue
        val = _num(tips.get(ind))
        if val is None:
            continue
        # Normalize Forex Reserves → currency proxy scale (~USDINR-like) when USDINR absent
        if ind == "Forex Reserves" and "USDINR" not in tips:
            # Map reserves bn into a soft currency-stress proxy (higher reserves → lower stress)
            # Keep raw reserves/10 so distance remains meaningful vs catalog USDINR when mixed —
            # prefer catalog currency for historical; for current use CMKP INR reference if any.
            continue
        features[dim] = val
    return features


def soft_hmip_period_features(period: str, *, country: str = "India") -> dict[str, float]:
    """Read HMIP store tips for a calendar year — never triggers collectors."""
    tips: dict[str, float | None] = {}
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator
    except Exception:
        return {}

    lookups = [
        ("Repo Rate", country),
        ("CPI", country),
        ("GDP", country),
        ("Banking Liquidity", country),
        ("Fiscal Deficit", country),
        ("WPI", country),
        ("Credit Growth", country),
        ("WEO Global Growth", "Global"),
    ]
    for name, ctry in lookups:
        try:
            pack = hmip_indicator(name, country=ctry)
        except Exception:
            continue
        if not pack.get("found"):
            continue
        series = pack.get("series") or pack.get("observations") or []
        val = None
        for obs in series:
            p = str(obs.get("period") or "")
            if p == period or p.startswith(period):
                val = _num(obs.get("value") or obs.get("current_value"))
                if val is not None:
                    break
        if val is None and series and period[:4].isdigit():
            year = int(period[:4])
            for obs in series:
                p = str(obs.get("period") or "")[:4]
                if p.isdigit() and abs(int(p) - year) <= 1:
                    val = _num(obs.get("value") or obs.get("current_value"))
                    if val is not None:
                        break
        tips[name] = val
    return features_from_indicator_tips(tips)


def enrich_regime_from_hmip(regime: MacroRegime) -> MacroRegime:
    """Overlay HMIP tip values onto catalog features when present."""
    hmip_feats = soft_hmip_period_features(regime.period, country=regime.country)
    if not hmip_feats:
        return regime
    merged = {**regime.features, **hmip_feats}
    layers = list(dict.fromkeys([*regime.source_layers, "HMIP"]))
    return regime.model_copy(
        update={
            "features": merged,
            "source_layers": layers,
            "provenance": {
                **regime.provenance,
                "hmip_overlay_keys": list(hmip_feats.keys()),
            },
        }
    )


def soft_cmkp_current_features(*, country: str = "India") -> tuple[dict[str, float], dict[str, Any]]:
    """Build current regime features from published CMKP tip — never collects."""
    tips: dict[str, float | None] = {}
    meta: dict[str, Any] = {"gateway": "CMKP_KRIG", "collected_on_request": False}
    try:
        from continuous_macro_knowledge.production import india as cmkp_india
        from continuous_macro_knowledge.production import indicator as cmkp_indicator
        from continuous_macro_knowledge.production import global_macro as cmkp_global
    except Exception:
        return {}, {**meta, "available": False}

    india = cmkp_india(limit=80)
    meta["published_count"] = india.get("n") or 0
    for name in (
        "Repo Rate",
        "CPI",
        "GDP",
        "Banking Liquidity",
        "Fiscal Deficit",
        "WPI",
        "Credit Growth",
        "Forex Reserves",
    ):
        try:
            pack = cmkp_indicator(name, country=country)
        except Exception:
            continue
        if pack.get("found"):
            latest = pack.get("latest") or {}
            tips[name] = _num(latest.get("current_value"))
            # INR reference from forex payload when present
            if name == "Forex Reserves":
                payload = (latest.get("normalized") or {}).get("payload") or {}
                inr = _num(payload.get("inr_reference"))
                if inr is not None:
                    tips["USDINR"] = inr
    # Global growth
    try:
        g = cmkp_global(limit=40)
        meta["global_published"] = g.get("n") or 0
        for name in ("WEO Global Growth", "World Bank Global Growth"):
            pack = cmkp_indicator(name, country="Global")
            if pack.get("found"):
                tips[name] = _num((pack.get("latest") or {}).get("current_value"))
        fed = cmkp_indicator("Federal Funds Rate", country="United States")
        if fed.get("found"):
            payload = ((fed.get("latest") or {}).get("normalized") or {}).get("payload") or {}
            gsec = _num(payload.get("us_treasury_10y"))
            # Soft India G-Sec proxy when local series absent: US 10Y + India term premium ~2.6
            if gsec is not None and "G-Sec 10Y" not in tips:
                tips["G-Sec 10Y"] = round(gsec + 2.6, 2)
    except Exception:
        pass

    features = features_from_indicator_tips(tips)
    # If Forex Reserves present but USDINR missing, leave currency empty for catalog fill
    meta["indicator_tips"] = {k: v for k, v in tips.items() if v is not None}
    meta["available"] = bool(features)
    meta["providers_queried"] = []
    return features, meta


def build_current_regime(*, country: str = "India", period: str | None = None) -> MacroRegime:
    """Current macro regime: CMKP tip preferred, catalog 2025 as soft fallback base."""
    feats, meta = soft_cmkp_current_features(country=country)
    base = next((r for r in catalog_regimes(country=country) if r.period == "2025"), None)
    base_feats = dict(base.features) if base else {}
    # Prefer live CMKP where present; keep catalog fill for missing dims (explainable)
    merged = {**base_feats, **feats}
    cur_period = period or "2026"
    layers = ["CMKP"] if feats else []
    if base:
        layers.append("hmai_regime_catalog_fill")
    return MacroRegime(
        country=country,
        period=cur_period,
        label=f"{country} {cur_period} current regime",
        features=merged,
        feature_units=dict(FEATURE_UNITS),
        outcome=None,
        equity_outcome=None,
        timeline_refs=["india:current:CMKP"],
        research_refs=["Macro Research Office: current conditions"],
        source_layers=layers or ["hmai_regime_catalog_fill"],
        provenance={"cmkp": meta, "fill_from_catalog_period": "2025" if base else None},
    )


def build_historical_regimes(*, country: str = "India", enrich_hmip: bool = True) -> list[MacroRegime]:
    regimes = catalog_regimes(country=country)
    if not enrich_hmip:
        return regimes
    return [enrich_regime_from_hmip(r) for r in regimes]


def soft_mri_relationships_for_dims(features: dict[str, float]) -> list[dict[str, Any]]:
    """Attach relevant MRI edges for explainability — store-only."""
    out: list[dict[str, Any]] = []
    try:
        from macroeconomic_relationship_intelligence.production import (
            for_indicator as mri_for_indicator,
        )
    except Exception:
        return out

    indicator_map = {
        "interest_rate": "Repo Rate",
        "inflation": "CPI",
        "currency": "USDINR",
        "liquidity": "Banking Liquidity",
        "fiscal": "Fiscal Deficit",
        "gdp": "GDP",
    }
    seen: set[str] = set()
    for dim, ind in indicator_map.items():
        if dim not in features:
            continue
        try:
            pack = mri_for_indicator(ind, limit=5)
        except Exception:
            continue
        for rel in pack.get("relationships") or []:
            rid = rel.get("relationship_id") or f"{rel.get('source')}->{rel.get('target')}"
            if rid in seen:
                continue
            seen.add(rid)
            out.append(
                {
                    "relationship_id": rid,
                    "source": rel.get("source"),
                    "target": rel.get("target"),
                    "relationship": rel.get("relationship"),
                    "confidence_pct": rel.get("confidence_pct"),
                    "dimension": dim,
                    "gateway": "MRI_KRIG",
                }
            )
        if len(out) >= 12:
            break
    return out
