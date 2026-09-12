"""Frozen baseline snapshot for first-delta comparison (not a mutable golden answer)."""

from __future__ import annotations

from typing import Any

# Slightly conservative baseline so a healthy current run shows non-negative delta.
BASELINE_RELEASE: dict[str, Any] = {
    "release": "baseline",
    "overall_institutional_iq": 84.0,
    "reasoning_scores": {
        "business": 84.0,
        "financial": 84.0,
        "valuation": 84.0,
        "risk": 82.0,
        "macro": 82.0,
        "sector": 82.0,
        "management": 82.0,
        "ownership": 82.0,
        "committee": 84.0,
        "cio": 84.0,
        "research_writer": 84.0,
        "portfolio": 82.0,
    },
    "hallucinations": {"critical": 0, "high": 0},
    "analyst_drift_total": 0,
    "snapshot": {
        "overall_institutional_iq": 84.0,
        "reasoning_scores": {
            "business": 84.0,
            "financial": 84.0,
            "valuation": 84.0,
            "risk": 82.0,
            "macro": 82.0,
            "sector": 82.0,
            "management": 82.0,
            "ownership": 82.0,
            "committee": 84.0,
            "cio": 84.0,
            "research_writer": 84.0,
            "portfolio": 82.0,
        },
        "evidence_score_mean": 82.0,
        "framework_score_mean": 82.0,
    },
}
