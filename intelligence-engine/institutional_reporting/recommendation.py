"""Recommendation / conviction consistency helpers for IRE-01."""

from __future__ import annotations

from typing import Any

from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.schema import CONVICTIONS, RECOMMENDATIONS


def normalize_recommendation(value: str) -> str:
    return str(value or "").strip().upper()


def normalize_conviction(value: str) -> str:
    return str(value or "").strip().upper()


def business_quality_band(value: Any) -> str:
    """Map numeric or label business quality into a coarse band."""
    if isinstance(value, (int, float)):
        score = float(value)
        if score >= 85:
            return "Excellent"
        if score >= 70:
            return "Strong"
        if score >= 55:
            return "Adequate"
        return "Weak"
    text = str(value or "").strip().title()
    if text in {"Excellent", "Strong", "Adequate", "Weak"}:
        return text
    return text or "Unclear"


def recommendation_requires_conviction(recommendation: str) -> set[str]:
    rec = normalize_recommendation(recommendation)
    if rec in {"BUY", "SELL"}:
        return {"MEDIUM", "HIGH"}
    if rec == "AVOID":
        return {"MEDIUM", "HIGH"}
    # HOLD / WATCH may be LOW
    return {"LOW", "MEDIUM", "HIGH"}


def is_known_recommendation(recommendation: str) -> bool:
    return normalize_recommendation(recommendation) in RECOMMENDATIONS


def is_known_conviction(conviction: str) -> bool:
    return normalize_conviction(conviction) in CONVICTIONS


def describe_alignment(inp: InstitutionalReportInput) -> str:
    return (
        f"Recommendation {normalize_recommendation(inp.recommendation)} with "
        f"{normalize_conviction(inp.conviction)} conviction."
    )
