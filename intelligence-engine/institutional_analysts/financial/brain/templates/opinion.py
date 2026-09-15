"""Financial Analyst structured opinion template."""

from __future__ import annotations

from typing import Any, Dict


def build_structured_opinion(payload: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "executive_opinion",
        "financial_quality",
        "profitability",
        "growth_quality",
        "earnings_quality",
        "cash_flow",
        "balance_sheet",
        "capital_allocation",
        "financial_dna",
        "historical_trend",
        "benchmarking",
        "assumptions",
        "uncertainties",
        "missing_evidence",
        "confidence",
        "quality_checks",
    )
    return {k: payload.get(k) for k in keys}
