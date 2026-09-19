"""Attach macro backdrop relevant to the question."""

from __future__ import annotations

import re
from typing import Any


def detect_macro_context(
    question: str,
    *,
    primary_objective: str | None = None,
) -> dict[str, Any]:
    text = question or ""
    factors: list[str] = []
    if re.search(r"\b(rbi|rate\s+cut|rate\s+hike|interest\s+rates?|mpc)\b", text, re.I):
        factors.extend(["Interest Rates", "Liquidity"])
    if re.search(r"\b(inflation|cpi|wpi)\b", text, re.I):
        factors.append("Inflation")
    if re.search(r"\b(gdp|growth)\b", text, re.I):
        factors.append("GDP")
    if re.search(r"\b(usd|inr|currency|rupee|dollar)\b", text, re.I):
        factors.append("Currency")
    if re.search(r"\b(oil|brent|crude)\b", text, re.I):
        factors.append("Oil")
    if re.search(r"\b(fiscal|budget)\b", text, re.I):
        factors.append("Fiscal Policy")
    if re.search(r"\b(regulation|regulatory|sebi|rbi\s+guidelines)\b", text, re.I):
        factors.append("Regulation")
    if re.search(r"\b(fed|global\s+risk|geopolitics)\b", text, re.I):
        factors.append("Global Risk")

    # Objective defaults
    if primary_objective == "Historical Analysis" and "IT" in text.upper():
        for f in ("US tech spending", "Currency", "USDINR"):
            if f not in factors:
                factors.append(f)
    if primary_objective in {"Investment Evaluation", "Macro Impact"} and not factors:
        factors = ["Interest Rates", "Inflation", "Liquidity", "Credit"]
    if primary_objective == "Macro Impact" and "Interest Rates" not in factors:
        factors.insert(0, "Interest Rates")

    summary = "Stable Rates; Moderating Inflation" if primary_objective == "Investment Evaluation" else (
        "Policy / cycle sensitive macro" if factors else "Standard macro backdrop"
    )
    if primary_objective == "Investment Evaluation":
        environment = "Moderately restrictive rates; Cooling inflation; Stable credit growth"
    elif primary_objective == "Historical Analysis":
        environment = "US tech spending; USDINR relevant"
    else:
        environment = summary

    return {
        "factors": factors,
        "interest_rates": "Stable / moderately restrictive",
        "inflation": "Moderating",
        "gdp": "Steady",
        "currency": "USDINR watch" if "Currency" in factors or "USDINR" in factors else "Neutral",
        "oil": "Neutral",
        "liquidity": "Adequate",
        "fiscal_policy": "Neutral",
        "regulation": "In focus" if "Regulation" in factors else "Standard",
        "global_risk": "In focus" if "Global Risk" in factors else "Contained",
        "environment": environment,
        "summary": summary,
        "required": bool(factors) or primary_objective in {"Macro Impact", "Investment Evaluation", "Historical Analysis"},
        "confidence": 0.93 if factors else 0.8,
    }
