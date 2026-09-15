"""Historical financial outcomes and lessons."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import as_list, txt


SEED_PATHS: dict[str, list[dict[str, Any]]] = {
    "HDFCBANK": [
        {"year": 2019, "theme": "returns_strength", "note": "ROE / operating profitability supportive"},
        {"year": 2020, "theme": "stress_test", "note": "COVID stress tested credit costs and resilience"},
        {"year": 2021, "theme": "recovery", "note": "Earnings and cash generation recovered with loan growth"},
        {"year": 2022, "theme": "integration", "note": "Merger enlarged balance sheet; mix and capital intensity rose"},
        {"year": 2023, "theme": "margin_pressure", "note": "Liability costs and mix began to pressure spreads"},
        {"year": 2024, "theme": "funding_competition", "note": "Deposit competition challenged historical funding advantage"},
    ],
}


def build_historical(
    *,
    company: str,
    ticker: str | None,
    frameworks: dict[str, Any],
    cases: dict[str, Any],
) -> dict[str, Any]:
    key = (ticker or "").upper()
    timeline = list(SEED_PATHS.get(key) or [])
    trend = (frameworks.get("trends") or {}).get("overall") or "Stable"
    lessons = list(cases.get("lessons_from_cases") or [])[:4]
    if timeline and any(e.get("theme") in {"margin_pressure", "funding_competition"} for e in timeline[-2:]):
        narrative = (
            f"Although {company}'s longer-term financial quality remains institutional, recent periods show "
            "funding-cost and spread pressure. Cash generation and capital strength still matter more than "
            "any single-period print."
        )
        lessons.append(
            "Financial quality can remain high while near-term return trajectories soften — separate level from trend."
        )
    elif timeline:
        narrative = (
            f"Historical financial path for {company}: "
            + " → ".join(f"{e.get('year')} {e.get('note')}" for e in timeline[-5:])
        )
    else:
        narrative = (
            f"No seeded multi-year financial path for {company}; lessons currently drawn from "
            f"archetype/case analogues and the assembled statement history."
        )

    return {
        "timeline": timeline,
        "overall_trend": trend,
        "historical_narrative": narrative,
        "lessons_learned": [x for x in lessons if x][:8],
        "component_trajectories": {
            "revenue": (frameworks.get("growth_quality") or {}).get("trajectory"),
            "margins": (frameworks.get("profitability") or {}).get("trajectory"),
            "cash_flow": (frameworks.get("cash_flow") or {}).get("trajectory"),
            "roic": (frameworks.get("returns") or {}).get("trajectory"),
            "leverage": (frameworks.get("balance_sheet") or {}).get("trajectory"),
            "capital_allocation": "Improving"
            if (frameworks.get("capital_allocation") or {}).get("shareholder_value_created")
            else "Stable",
        },
        "history_notes": as_list(timeline and [txt(e.get("note")) for e in timeline], limit=6),
    }
