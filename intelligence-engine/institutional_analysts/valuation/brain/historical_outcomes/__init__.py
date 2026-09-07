"""Historical valuation outcomes and lessons."""

from __future__ import annotations

from typing import Any


def build_historical(
    *,
    company: str,
    frameworks: dict[str, Any],
    cases: dict[str, Any],
) -> dict[str, Any]:
    hist = frameworks.get("historical_valuation") or {}
    mos = frameworks.get("margin_of_safety") or {}
    lessons = list(cases.get("lessons_from_cases") or [])[:5]
    narrative = (
        f"For {company}, historical valuation context is {str(hist.get('current_vs_history') or 'mixed').lower()}. "
        f"Margin-of-safety character is {str(mos.get('downside_protection') or 'mixed').lower()}. "
        "Multiple changes should be read as expectation changes, not isolated ratio moves."
    )
    return {
        "historical_narrative": narrative,
        "current_vs_history": hist.get("current_vs_history"),
        "lessons_learned": lessons,
        "multiple_trend": hist.get("current_vs_history"),
        "expectation_trend": (frameworks.get("market_expectations") or {}).get("premium_or_discount"),
    }
