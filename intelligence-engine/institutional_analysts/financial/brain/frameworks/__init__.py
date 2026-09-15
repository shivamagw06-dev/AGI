"""Financial Analyst frameworks — apply all to assembled evidence only."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain.frameworks import (
    balance_sheet,
    capital_allocation,
    cash_flow,
    durability,
    earnings_quality,
    growth_quality,
    profitability,
    returns,
    trends,
)


def apply_all(evidence: dict[str, Any]) -> dict[str, Any]:
    profit = profitability.assess(evidence)
    rets = returns.assess(evidence)
    growth = growth_quality.assess(evidence)
    earnings = earnings_quality.assess(evidence)
    cash = cash_flow.assess(evidence)
    bs = balance_sheet.assess(evidence)
    capital = capital_allocation.assess(evidence)
    pieces = {
        "profitability": profit,
        "returns": rets,
        "growth_quality": growth,
        "earnings_quality": earnings,
        "cash_flow": cash,
        "balance_sheet": bs,
        "capital_allocation": capital,
    }
    durable = durability.assess(evidence, pieces)
    trend = trends.assess(evidence, pieces)
    pieces["durability"] = durable
    pieces["trends"] = trend

    return {
        "applied": [
            profit["framework"],
            rets["framework"],
            growth["framework"],
            earnings["framework"],
            cash["framework"],
            bs["framework"],
            capital["framework"],
            durable["framework"],
            trend["framework"],
            "Financial DNA",
            "Benchmarking",
            "Case Library",
        ],
        **pieces,
    }
