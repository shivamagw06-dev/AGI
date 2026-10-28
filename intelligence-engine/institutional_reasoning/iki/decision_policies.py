"""Module 5 — Decision Policies.

Committee weights by question type — not intuition.
"""

from __future__ import annotations

from typing import Any

POLICIES_VERSION = "decision-policies-v1.0.0"

POLICIES: dict[str, dict[str, float]] = {
    "investment_decision": {
        "business_quality": 0.30,
        "valuation": 0.30,
        "accounting": 0.20,
        "risk": 0.20,
    },
    "valuation": {
        "valuation": 0.55,
        "business_quality": 0.20,
        "accounting": 0.15,
        "risk": 0.10,
    },
    "business_quality": {
        "business_quality": 0.60,
        "accounting": 0.25,
        "valuation": 0.10,
        "risk": 0.05,
    },
    "financial_quality": {
        "accounting": 0.70,
        "business_quality": 0.15,
        "risk": 0.10,
        "valuation": 0.05,
    },
    "comparison": {
        "valuation": 0.40,
        "business_quality": 0.35,
        "accounting": 0.15,
        "risk": 0.10,
    },
}


def policy_for(question_type: str) -> dict[str, Any]:
    qt = str(question_type or "").lower()
    weights = dict(POLICIES.get(qt) or POLICIES["valuation"])
    return {
        "question_type": qt,
        "weights": weights,
        "policies_version": POLICIES_VERSION,
        "note": "Committee follows policy weights; does not invent intuition.",
    }


def dominant_lens(question_type: str) -> str:
    p = policy_for(question_type)
    weights = p["weights"]
    return max(weights.items(), key=lambda kv: kv[1])[0]
