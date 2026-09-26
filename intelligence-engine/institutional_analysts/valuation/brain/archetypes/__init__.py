"""Valuation archetypes — pattern labels aligned with Valuation DNA."""

from __future__ import annotations

from typing import Any


def match_archetype(dna: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    profile = str(dna.get("profile") or "Fairly Valued Compounder")
    bias = 0.0
    if "Premium" in profile:
        bias = -0.03
    elif "Deep Value" in profile:
        bias = 0.04
    elif "Speculative" in profile or "High Growth" in profile:
        bias = -0.06
    return {
        "primary": {
            "name": profile,
            "pattern": [
                str((frameworks.get("market_expectations") or {}).get("premium_or_discount") or ""),
                str((frameworks.get("margin_of_safety") or {}).get("downside_protection") or ""),
            ],
            "confidence_bias": bias,
        },
        "template_reasoning": f"Valuation archetype: {profile}.",
    }
