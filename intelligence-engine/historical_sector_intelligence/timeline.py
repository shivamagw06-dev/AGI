"""Historical Sector Timeline Builder."""

from __future__ import annotations

from typing import Any

from historical_sector_intelligence.collectors import SECTOR_EVENT_ANCHORS
from historical_sector_intelligence.schema import SectorTimeline, TimelineNode
from historical_sector_intelligence.store import STORE


def _year(period: str) -> int | None:
    raw = str(period or "").replace("FY", "")
    try:
        return int(raw[:4])
    except ValueError:
        return None


def build_timeline(sector_key: str, *, indicator: str = "Revenue Growth") -> SectorTimeline:
    series = STORE.series(indicator, sector_key=sector_key)
    anchors = SECTOR_EVENT_ANCHORS.get(sector_key) or {}
    nodes: list[TimelineNode] = []
    years: list[int] = []
    label = series[0].sector_label if series else sector_key
    category = series[0].category if series else "Growth"

    # Prefer event observations for narrative when building primary timeline
    event_by_year: dict[int, str] = {}
    event_series = STORE.series("Key Event", sector_key=sector_key)
    for eobs in event_series:
        ey = _year(eobs.period)
        if ey is not None and eobs.key_events:
            event_by_year[ey] = eobs.key_events[0]

    for obs in series:
        y = _year(obs.period)
        if y is None:
            continue
        years.append(y)
        event = anchors.get(y) or event_by_year.get(y)
        if not event and obs.key_events:
            event = obs.key_events[0]
        importance = "Critical" if event else ("High" if obs.value is not None else "Medium")
        nodes.append(
            TimelineNode(
                year=y,
                period=obs.period,
                label=f"{label} {obs.period}",
                value=obs.value,
                importance=importance,
                event=event,
                hsko_id=obs.hsko_id,
                sector_leader=obs.sector_leader,
                macro_regime=obs.macro_regime,
            )
        )

    # Ensure anchor years appear even if metric missing
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
                    macro_regime=None,
                )
            )
            years.append(y)

    nodes.sort(key=lambda n: n.year)
    years = sorted(set(years))
    expected = sorted(set(anchors) | set(years))
    missing = [str(y) for y in expected if y not in present] if expected else []
    completeness = (
        round(100.0 * len(present) / max(len(expected), 1), 2) if expected else 0.0
    )

    timeline = SectorTimeline(
        sector_key=sector_key,
        sector_label=label,
        indicator=indicator,
        category=category,
        nodes=nodes,
        years_span=years,
        completeness_pct=completeness,
        missing_periods=missing,
    )
    return STORE.put_timeline(timeline)


def build_all_timelines() -> dict[str, Any]:
    # Primary growth timeline per sector + valuation PE timeline for deep sectors
    sectors = sorted({r.sector_key for r in STORE.list_all(limit=5000)})
    built = 0
    for sk in sectors:
        build_timeline(sk, indicator="Revenue Growth")
        built += 1
        if sk in SECTOR_EVENT_ANCHORS:
            build_timeline(sk, indicator="Average PE")
            built += 1
    return {"n": built, "sectors": len(sectors)}
