"""Valuation structured opinion template."""

from __future__ import annotations

from typing import Any, Dict


def build_structured_opinion(payload: Dict[str, Any]) -> Dict[str, Any]:
    keys = (
        "executive_opinion",
        "intrinsic_value_view",
        "market_expectations",
        "valuation_quality",
        "multiple_analysis",
        "dcf_discussion",
        "relative_valuation",
        "historical_valuation",
        "margin_of_safety",
        "valuation_dna",
        "historical_trend",
        "peer_comparison",
        "assumptions",
        "uncertainties",
        "missing_evidence",
        "confidence",
        "quality_checks",
    )
    return {k: payload.get(k) for k in keys}
