"""Framework 9 — Trend Analysis."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import as_list, txt, trend_label


def assess(evidence: dict[str, Any], pieces: dict[str, Any]) -> dict[str, Any]:
    trend = txt(evidence.get("trend"))
    narrative = txt(evidence.get("narrative"))
    history = as_list(evidence.get("history_notes") or evidence.get("multi_year_history"), limit=6)
    quarterly = as_list(evidence.get("quarterly_history"), limit=4)
    label = trend_label(trend or narrative)

    # Compose from component trajectories
    comps = {
        "profitability": (pieces.get("profitability") or {}).get("trajectory"),
        "returns": (pieces.get("returns") or {}).get("trajectory"),
        "cash_flow": (pieces.get("cash_flow") or {}).get("trajectory"),
        "growth": (pieces.get("growth_quality") or {}).get("trajectory"),
        "balance_sheet": (pieces.get("balance_sheet") or {}).get("trajectory"),
    }
    improving_n = sum(1 for v in comps.values() if v in {"Improving", "Accelerating"})
    weakening_n = sum(1 for v in comps.values() if v in {"Weakening", "Decelerating"})
    if improving_n > weakening_n and improving_n >= 2:
        overall = "Improving"
    elif weakening_n > improving_n and weakening_n >= 2:
        overall = "Weakening"
    else:
        overall = label

    return {
        "framework": "Trend Analysis",
        "completed": bool(trend or narrative or history or quarterly or any(comps.values())),
        "five_year": history[:3] or ["Multi-year history under review"],
        "ten_year": history or ["Longer history sparse in current file"],
        "quarterly": quarterly or ["Quarterly sequence under review"],
        "ttm": trend or narrative or "TTM trajectory under review",
        "annual": history[:2] or [trend or "Annual trajectory under review"],
        "components": comps,
        "overall": overall,
        "assessment": (
            f"Financial trends are {overall.lower()} across profitability, returns and cash conversion lenses."
        ),
    }
