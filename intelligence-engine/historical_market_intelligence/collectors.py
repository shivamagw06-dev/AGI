"""Historical market collectors — seeded institutional memory (ops-derived, not live APIs).

Soft-aligned with CMKTP universe. Groww/Yahoo appear only as provenance labels.
Ask never invokes these.
"""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MARKET_UNIVERSE
from historical_market_intelligence.schema import RawHistoricalMarketObservation

MARKET_LABELS: dict[str, str] = {
    "india_equity": "India Equity Market",
    "global_equity": "Global Equity Markets",
    "breadth": "Market Breadth",
    "liquidity": "Market Liquidity",
    "volatility": "Market Volatility",
    "institutional_flows": "Institutional Flows",
    "leadership": "Market Leadership",
    "cross_asset": "Cross-Asset State",
    "risk_sentiment": "Risk Sentiment",
    "market_health": "Market Health",
}

# Institutional timeline anchors (India equity — spec)
MARKET_EVENT_ANCHORS: dict[str, dict[int, str]] = {
    "india_equity": {
        2000: "Dot-com Crash",
        2003: "2003 Bull Market",
        2008: "2008 GFC",
        2013: "2013 Taper Tantrum",
        2016: "2016 Demonetisation",
        2020: "2020 COVID Crash",
        2021: "2021 Recovery",
        2022: "2022 Inflation Shock",
        2026: "Current",
    },
    "global_equity": {
        2008: "Global GFC",
        2020: "Global COVID Crash",
        2022: "Global Inflation Shock",
        2026: "Current",
    },
    "volatility": {
        2008: "GFC vol spike",
        2020: "COVID vol spike",
        2022: "Inflation vol regime",
        2026: "Vol compression era",
    },
    "institutional_flows": {
        2013: "FII taper episode",
        2020: "COVID FII selling",
        2022: "Inflation flow stress",
        2026: "DII cushion era",
    },
    "cross_asset": {
        2008: "Flight to quality",
        2020: "COVID cross-asset stress",
        2022: "USD/oil shock",
        2026: "Current",
    },
}

# period -> (health, breadth, liquidity, volatility, flows, leadership)
MARKET_METRIC_SEEDS: dict[str, dict[str, tuple[float, float, float, float, float, float]]] = {
    "india_equity": {
        "FY2000": (28.0, 25.0, 30.0, 85.0, 22.0, 30.0),
        "FY2003": (72.0, 70.0, 68.0, 40.0, 65.0, 74.0),
        "FY2008": (22.0, 18.0, 25.0, 90.0, 15.0, 20.0),
        "FY2013": (42.0, 40.0, 45.0, 62.0, 35.0, 44.0),
        "FY2016": (48.0, 46.0, 50.0, 58.0, 42.0, 50.0),
        "FY2020": (20.0, 15.0, 22.0, 92.0, 18.0, 18.0),
        "FY2021": (75.0, 72.0, 78.0, 38.0, 70.0, 76.0),
        "FY2022": (50.0, 48.0, 52.0, 68.0, 40.0, 55.0),
        "FY2026": (62.0, 58.0, 64.0, 45.0, 60.0, 63.0),
    },
    "global_equity": {
        "FY2008": (18.0, 16.0, 20.0, 88.0, 14.0, 18.0),
        "FY2020": (22.0, 20.0, 24.0, 90.0, 20.0, 22.0),
        "FY2022": (48.0, 45.0, 50.0, 65.0, 42.0, 50.0),
        "FY2026": (60.0, 58.0, 62.0, 42.0, 58.0, 60.0),
    },
}


def _obs(
    *,
    source: str,
    market_key: str,
    market_label: str,
    category: str,
    indicator: str,
    value: float | None,
    period: str,
    previous: float | None = None,
    unit: str = "",
    market_regime: str | None = None,
    breadth_state: str | None = None,
    liquidity_state: str | None = None,
    volatility_state: str | None = None,
    institutional_flows: str | None = None,
    leadership: str | None = None,
    cross_asset_state: str | None = None,
    major_events: list[str] | None = None,
    publication_date: str | None = None,
    payload: dict[str, Any] | None = None,
) -> RawHistoricalMarketObservation:
    year = period.replace("FY", "")[:4]
    pub = publication_date or (f"{year}-03-31" if year.isdigit() else "2000-03-31")
    return RawHistoricalMarketObservation(
        source=source,
        market_key=market_key,
        market_label=market_label,
        category=category,
        indicator=indicator,
        value=value,
        period=period,
        previous=previous,
        unit=unit,
        market_regime=market_regime,
        breadth_state=breadth_state,
        liquidity_state=liquidity_state,
        volatility_state=volatility_state,
        institutional_flows=institutional_flows,
        leadership=leadership,
        cross_asset_state=cross_asset_state,
        major_events=major_events or [],
        publication_date=pub,
        effective_date=period,
        payload=payload or {},
    )


def _regime_for_year(year: int) -> str:
    if year in {2000, 2008, 2020}:
        return "Bear"
    if year in {2003, 2021}:
        return "Bull"
    if year in {2013, 2016}:
        return "Correction"
    if year == 2022:
        return "Distribution"
    if year >= 2023:
        return "Sideways"
    return "Mixed"


def _state(score: float, *, invert: bool = False) -> str:
    s = (100.0 - score) if invert else score
    if s >= 70:
        return "strong"
    if s >= 55:
        return "adequate"
    if s >= 40:
        return "mixed"
    return "weak"


def _source_for(market_key: str) -> str:
    if market_key in {
        "india_equity",
        "breadth",
        "liquidity",
        "institutional_flows",
        "leadership",
        "market_health",
    }:
        return "groww_historical_seed"
    if market_key in {"global_equity", "cross_asset", "volatility", "risk_sentiment"}:
        return "yahoo_finance_historical_seed"
    return "agi_internal_historical"


def _metric_rows(market_key: str) -> list[RawHistoricalMarketObservation]:
    label = MARKET_LABELS.get(market_key, market_key)
    seeds = MARKET_METRIC_SEEDS.get(market_key)
    rows: list[RawHistoricalMarketObservation] = []
    if not seeds:
        # Light default for remaining universe domains
        seeds = {
            "FY2018": (58.0, 55.0, 56.0, 48.0, 54.0, 57.0),
            "FY2020": (25.0, 20.0, 28.0, 88.0, 22.0, 24.0),
            "FY2022": (50.0, 48.0, 52.0, 66.0, 44.0, 52.0),
            "FY2026": (61.0, 58.0, 63.0, 44.0, 59.0, 62.0),
        }
    prev: dict[str, float | None] = {
        "health": None,
        "breadth": None,
        "liquidity": None,
        "volatility": None,
        "flows": None,
        "leadership": None,
    }
    source = _source_for(market_key)
    for period, (health, breadth, liquidity, vol, flows, leadership) in sorted(seeds.items()):
        year = int(period.replace("FY", "")[:4])
        regime = _regime_for_year(year)
        event = (MARKET_EVENT_ANCHORS.get(market_key) or {}).get(year)
        events = [event] if event else []
        b_state = _state(breadth)
        l_state = _state(liquidity)
        v_state = _state(vol, invert=True)
        f_state = "outflow" if flows < 40 else "mixed" if flows < 55 else "inflow"
        lead_state = _state(leadership)
        x_state = "risk_off" if vol >= 70 else "mixed" if vol >= 50 else "risk_on"

        common = dict(
            source=source,
            market_key=market_key,
            market_label=label,
            market_regime=regime,
            breadth_state=b_state,
            liquidity_state=l_state,
            volatility_state=v_state,
            institutional_flows=f_state,
            leadership=lead_state,
            cross_asset_state=x_state,
            major_events=events,
            payload={
                "ops_sources": ["Groww Historical", "Yahoo Finance", "AGI internal history"],
                "ask_safe": True,
            },
        )

        rows.append(
            _obs(
                **common,
                category="Health",
                indicator="Market Health",
                value=health,
                period=period,
                previous=prev["health"],
                unit="index",
            )
        )
        rows.append(
            _obs(
                **common,
                category="Breadth",
                indicator="Advance Decline",
                value=breadth,
                period=period,
                previous=prev["breadth"],
                unit="index",
            )
        )
        rows.append(
            _obs(
                **common,
                category="Liquidity",
                indicator="Trading Volume Index",
                value=liquidity,
                period=period,
                previous=prev["liquidity"],
                unit="index",
            )
        )
        rows.append(
            _obs(
                **common,
                category="Volatility",
                indicator="Realised Volatility",
                value=vol,
                period=period,
                previous=prev["volatility"],
                unit="index",
            )
        )
        rows.append(
            _obs(
                **common,
                category="Flows",
                indicator="Net Institutional Flow",
                value=flows,
                period=period,
                previous=prev["flows"],
                unit="index",
            )
        )
        rows.append(
            _obs(
                **common,
                category="Leadership",
                indicator="Leadership Score",
                value=leadership,
                period=period,
                previous=prev["leadership"],
                unit="index",
            )
        )
        rows.append(
            _obs(
                **common,
                category="Cycles",
                indicator="Market Regime",
                value=health,
                period=period,
                previous=prev["health"],
                unit="regime_score",
            )
        )
        if market_key == "cross_asset" or market_key == "global_equity":
            rows.append(
                _obs(
                    **common,
                    category="CrossAsset",
                    indicator="Cross Asset Stress",
                    value=vol,
                    period=period,
                    previous=prev["volatility"],
                    unit="index",
                )
            )

        prev = {
            "health": health,
            "breadth": breadth,
            "liquidity": liquidity,
            "volatility": vol,
            "flows": flows,
            "leadership": leadership,
        }
    return rows


def _event_rows(market_key: str) -> list[RawHistoricalMarketObservation]:
    label = MARKET_LABELS.get(market_key, market_key)
    anchors = MARKET_EVENT_ANCHORS.get(market_key) or {}
    source = _source_for(market_key)
    rows: list[RawHistoricalMarketObservation] = []
    for year, event in sorted(anchors.items()):
        period = f"FY{year}"
        rows.append(
            _obs(
                source=source,
                market_key=market_key,
                market_label=label,
                category="Events",
                indicator="Key Event",
                value=None,
                period=period,
                market_regime=_regime_for_year(year),
                major_events=[event],
                payload={"anchor": True, "ask_safe": True},
            )
        )
    return rows


def collect_source(source_id: str) -> dict[str, Any]:
    """Collect for a named provenance source id."""
    try:
        if source_id == "groww_historical":
            markets = [
                m
                for m in MARKET_UNIVERSE
                if _source_for(m) == "groww_historical_seed"
            ]
        elif source_id == "yahoo_finance_historical":
            markets = [
                m
                for m in MARKET_UNIVERSE
                if _source_for(m) == "yahoo_finance_historical_seed"
            ]
        elif source_id == "agi_internal":
            markets = list(MARKET_UNIVERSE)
        else:
            return {"ok": False, "n": 0, "observations": [], "error": "unknown_source"}

        observations: list[RawHistoricalMarketObservation] = []
        for mk in markets:
            observations.extend(_metric_rows(mk))
            observations.extend(_event_rows(mk))
        return {"ok": True, "n": len(observations), "observations": observations}
    except Exception as exc:  # pragma: no cover - defensive
        return {"ok": False, "n": 0, "observations": [], "error": str(exc)}


def collect_all() -> dict[str, Any]:
    by_source: dict[str, Any] = {}
    observations: list[RawHistoricalMarketObservation] = []
    for sid in ("groww_historical", "yahoo_finance_historical", "agi_internal"):
        out = collect_source(sid)
        # agi_internal duplicates — only use for domains already covered lightly:
        # skip agi_internal bulk to avoid triple-publish; keep health tick only
        by_source[sid] = {"ok": out.get("ok"), "n": out.get("n") or 0}
        if sid == "agi_internal":
            continue
        observations.extend(out.get("observations") or [])
    # Ensure every MARKET_UNIVERSE member has at least metric+event coverage
    covered = {o.market_key for o in observations}
    for mk in MARKET_UNIVERSE:
        if mk not in covered:
            observations.extend(_metric_rows(mk))
            observations.extend(_event_rows(mk))
    return {
        "ok": True,
        "by_source": by_source,
        "observations": observations,
        "n": len(observations),
        "ask_triggered": False,
        "providers_queried": [],
    }


def collect_markets(markets: list[str] | None = None) -> dict[str, Any]:
    selected = [m for m in (markets or list(MARKET_UNIVERSE)) if m in MARKET_UNIVERSE]
    observations: list[RawHistoricalMarketObservation] = []
    for mk in selected:
        observations.extend(_metric_rows(mk))
        observations.extend(_event_rows(mk))
    return {
        "ok": True,
        "observations": observations,
        "n": len(observations),
        "markets": selected,
        "ask_triggered": False,
        "providers_queried": [],
    }
