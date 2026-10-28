"""Historical Market Timeline Builder."""

from __future__ import annotations

from typing import Any

from historical_market_intelligence.collectors import MARKET_EVENT_ANCHORS, MARKET_LABELS
from historical_market_intelligence.schema import MarketTimeline, TimelineNode
from historical_market_intelligence.store import STORE


def _year(period: str) -> int | None:
    raw = str(period or "").replace("FY", "")
    try:
        return int(raw[:4])
    except ValueError:
        return None


def build_timeline(market_key: str, *, indicator: str = "Market Health") -> MarketTimeline:
    series = STORE.series(indicator, market_key=market_key)
    anchors = MARKET_EVENT_ANCHORS.get(market_key) or {}
    nodes: list[TimelineNode] = []
    years: list[int] = []
    label = series[0].market_label if series else MARKET_LABELS.get(market_key, market_key)

    event_by_year: dict[int, str] = {}
    event_series = STORE.series("Key Event", market_key=market_key)
    for eobs in event_series:
        ey = _year(eobs.period)
        if ey is not None and eobs.major_events:
            event_by_year[ey] = eobs.major_events[0]

    for obs in series:
        y = _year(obs.period)
        if y is None:
            continue
        years.append(y)
        event = anchors.get(y) or event_by_year.get(y)
        if not event and obs.major_events:
            event = obs.major_events[0]
        importance = "Critical" if event else ("High" if obs.value is not None else "Medium")
        nodes.append(
            TimelineNode(
                year=y,
                period=obs.period,
                label=f"{label} {obs.period}",
                value=obs.value,
                importance=importance,
                event=event,
                hmkto_id=obs.hmkto_id,
                market_regime=obs.market_regime,
            )
        )

    present = set(years)
    for y, event in anchors.items():
        if y not in present:
            nodes.append(
                TimelineNode(
                    year=y,
                    period=f"FY{y}",
                    label=f"{label} FY{y}",
                    value=None,
                    importance="Critical",
                    event=event,
                    market_regime=None,
                )
            )
            years.append(y)

    nodes.sort(key=lambda n: n.year or 0)
    years = sorted(set(years))
    expected = sorted(set(anchors) | set(years))
    missing = [str(y) for y in expected if y not in present] if expected else []
    completeness = (
        round(100.0 * len(present) / max(len(expected), 1), 2) if expected else 0.0
    )

    timeline = MarketTimeline(
        market_key=market_key,
        market_label=label,
        indicator=indicator,
        nodes=nodes,
        years_span=years,
        completeness_pct=completeness,
        missing_periods=missing,
    )
    return STORE.put_timeline(timeline)


def build_all_timelines() -> dict[str, Any]:
    markets = sorted({r.market_key for r in STORE.list_all(limit=5000)})
    built = 0
    for mk in markets:
        build_timeline(mk, indicator="Market Health")
        built += 1
        if mk in MARKET_EVENT_ANCHORS:
            build_timeline(mk, indicator="Advance Decline")
            built += 1
            build_timeline(mk, indicator="Realised Volatility")
            built += 1
    return {"n": built, "markets": len(markets)}
