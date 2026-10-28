"""Historical Timeline Builder — complete indicator timelines across decades."""

from __future__ import annotations

from typing import Any

from historical_macro_intelligence.schema import IndicatorTimeline, TimelineNode
from historical_macro_intelligence.store import STORE

# Institutional narrative anchors overlaid on numerical series
_EVENT_ANCHORS: dict[str, dict[int, str]] = {
    "Repo Rate": {
        1998: "High-rate era",
        2003: "Easing cycle",
        2008: "GFC tightening",
        2013: "Taper tantrum response",
        2016: "MPC framework",
        2020: "COVID emergency easing",
        2022: "Inflation fighting hike cycle",
        2025: "Current hold regime",
    },
    "GDP": {
        1995: "Reform expansion",
        1998: "Asian Crisis",
        2001: "Dot-com slowdown",
        2008: "GFC",
        2020: "COVID",
        2021: "Recovery",
        2025: "Current",
    },
    "CPI": {
        2013: "High inflation",
        2015: "Disinflation",
        2020: "COVID supply shock",
        2022: "Global inflation wave",
        2025: "Moderation",
    },
    "Federal Funds Rate": {
        2000: "Dot-com tightening",
        2009: "ZIRP",
        2020: "COVID emergency",
        2022: "Aggressive hiking",
        2025: "Restrictive plateau",
    },
    "Fiscal Deficit": {
        2008: "Crisis stimulus",
        2020: "COVID fiscal expansion",
        2025: "Consolidation path",
    },
}


def _year(period: str) -> int | None:
    raw = str(period or "")
    if raw.startswith("FY") and len(raw) >= 6:
        try:
            return int(raw[2:6])
        except ValueError:
            return None
    try:
        return int(raw[:4])
    except ValueError:
        return None


def build_timeline(indicator: str, *, country: str = "India") -> IndicatorTimeline:
    series = STORE.series(indicator, country=country)
    anchors = _EVENT_ANCHORS.get(indicator) or {}
    nodes: list[TimelineNode] = []
    years: list[int] = []

    for obs in series:
        y = _year(obs.period)
        if y is None:
            continue
        years.append(y)
        event = anchors.get(y)
        importance = "Critical" if event else ("High" if obs.value is not None else "Medium")
        nodes.append(
            TimelineNode(
                year=y,
                period=obs.period,
                label=f"{indicator} {obs.period}",
                value=obs.value,
                importance=importance,
                event=event,
                hmko_id=obs.hmko_id,
            )
        )

    # Completeness vs expected decade coverage when anchors exist
    expected_years = sorted(set(anchors) | set(years))
    missing = [str(y) for y in expected_years if y not in years] if expected_years else []
    # Also check for gaps in continuous span
    if years:
        full = list(range(min(years), max(years) + 1))
        # Annual series may intentionally skip — only flag missing anchor years as gaps
        completeness = round(100.0 * len(years) / max(len(expected_years), len(years)), 2)
    else:
        completeness = 0.0

    # Prefer completeness against anchors when present
    if anchors:
        hit = sum(1 for y in anchors if y in years)
        completeness = round(100.0 * hit / len(anchors), 2)
        missing = [str(y) for y in sorted(anchors) if y not in years]

    timeline = IndicatorTimeline(
        country=country,
        indicator=indicator,
        category=series[0].category if series else "Growth",
        nodes=nodes,
        years_span=[min(years), max(years)] if years else [],
        completeness_pct=completeness,
        missing_periods=missing,
    )
    return STORE.put_timeline(timeline)


def build_all_timelines() -> dict[str, Any]:
    """Build timelines for every indicator present in the store."""
    keys: set[tuple[str, str]] = set()
    for obs in STORE.list_all(limit=5000):
        keys.add((obs.country, obs.indicator))
    built = []
    for country, indicator in sorted(keys):
        tl = build_timeline(indicator, country=country)
        built.append(
            {
                "country": country,
                "indicator": indicator,
                "nodes": len(tl.nodes),
                "completeness_pct": tl.completeness_pct,
            }
        )
    return {"n": len(built), "timelines": built}
