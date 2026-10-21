"""Historical outcomes — timelines, quality paths, lessons (knowledge assets)."""

from institutional_analysts.business.brain.historical_outcomes.lessons import derive_lessons
from institutional_analysts.business.brain.historical_outcomes.timelines import (
    quality_path_for,
    timeline_for,
)


def build_historical_learning(
    *,
    company: str,
    ticker: str | None,
    cases: dict,
    archetype: dict,
    moat: dict,
    live_quality_path: list | None = None,
) -> dict:
    timeline = timeline_for(company, ticker)
    seeded = quality_path_for(company, ticker)
    path = list(live_quality_path or []) or seeded
    return derive_lessons(
        company=company,
        timeline=timeline,
        quality_path=path,
        cases=cases,
        archetype=archetype,
        moat=moat,
    )


__all__ = ["build_historical_learning", "timeline_for", "quality_path_for", "derive_lessons"]
