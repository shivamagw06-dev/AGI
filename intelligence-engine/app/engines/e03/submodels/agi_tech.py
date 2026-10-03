"""SM_AGI_TECH — behavioural migration of production score_research().

Source of truth: server/scripts/nifty500_research_engine.py
Every threshold, indicator contribution, and label must remain identical.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engines.e03.mapping import ALPHA_ID, SUBMODEL_ID
from app.engines.e03.submodels.label_bands import category


def score_research(indicators: dict[str, Any]) -> float:
    """AGI research score — verbatim production formula (P0 freeze)."""
    score = 50.0
    rsi = indicators["rsi"]
    score += 8 if rsi >= 60 else 3 if rsi >= 50 else -3 if rsi <= 40 else 0
    score += (
        7
        if indicators["macd_positive"] and indicators["macd_histogram"] > 0
        else -7
        if not indicators["macd_positive"] and indicators["macd_histogram"] < 0
        else 0
    )
    score += sum(
        (3 if flag else -3)
        for flag in (
            indicators["above_sma20"],
            indicators["above_sma50"],
            indicators["above_sma200"],
        )
    )
    score += 5 if indicators["sma20_above_sma50"] else -5
    score += 5 if indicators["change_20d"] > 2 else -5 if indicators["change_20d"] < -2 else 0
    score += 5 if indicators["change_60d"] > 5 else -5 if indicators["change_60d"] < -5 else 0
    score += (
        4
        if indicators["volume_ratio"] >= 1.2 and indicators["change_5d"] > 0
        else -4
        if indicators["volume_ratio"] >= 1.2 and indicators["change_5d"] < 0
        else 0
    )
    score += 5 if indicators["position_52w"] >= 0.7 else -5 if indicators["position_52w"] <= 0.3 else 0
    score += 3 if indicators["roc_10"] > 0 else -3 if indicators["roc_10"] < 0 else 0
    return round(max(0, min(100, score)), 1)


def confidence(score: float, indicators: dict[str, Any]) -> int:
    """Exact production `confidence()` → percent in [40, 95]."""
    direction = score >= 50
    checks = [
        indicators["rsi"] >= 50,
        indicators["macd_histogram"] > 0,
        indicators["above_sma50"],
        indicators["above_sma200"],
        indicators["change_20d"] > 0,
        indicators["change_60d"] > 0,
        indicators["position_52w"] >= 0.5,
    ]
    agreement = sum(check == direction for check in checks) / len(checks)
    return round(min(95, max(40, (50 + abs(score - 50)) * (0.7 + agreement * 0.3))))


@dataclass(frozen=True)
class SmAgiTechResult:
    submodel_id: str
    alpha_id: str
    agi_tech_score: float
    label: str
    confidence_pct: int
    confidence: float
    contributions: dict[str, float]


def run_sm_agi_tech(indicators: dict[str, Any]) -> SmAgiTechResult:
    """SM_AGI_TECH submodel entrypoint."""
    score = score_research(indicators)
    label = category(score)
    conf_pct = confidence(score, indicators)
    return SmAgiTechResult(
        submodel_id=SUBMODEL_ID,
        alpha_id=ALPHA_ID,
        agi_tech_score=score,
        label=label,
        confidence_pct=conf_pct,
        confidence=round(conf_pct / 100.0, 4),
        contributions=_contributions(indicators),
    )


def _contributions(indicators: dict[str, Any]) -> dict[str, float]:
    """Per-indicator signed contributions (same rules as score_research)."""
    rsi = indicators["rsi"]
    out: dict[str, float] = {
        "rsi": float(8 if rsi >= 60 else 3 if rsi >= 50 else -3 if rsi <= 40 else 0),
        "macd": float(
            7
            if indicators["macd_positive"] and indicators["macd_histogram"] > 0
            else -7
            if not indicators["macd_positive"] and indicators["macd_histogram"] < 0
            else 0
        ),
        "price_vs_sma": float(
            sum(
                (3 if flag else -3)
                for flag in (
                    indicators["above_sma20"],
                    indicators["above_sma50"],
                    indicators["above_sma200"],
                )
            )
        ),
        "sma_alignment": float(5 if indicators["sma20_above_sma50"] else -5),
        "change_20d": float(
            5 if indicators["change_20d"] > 2 else -5 if indicators["change_20d"] < -2 else 0
        ),
        "change_60d": float(
            5 if indicators["change_60d"] > 5 else -5 if indicators["change_60d"] < -5 else 0
        ),
        "volume_confirmation": float(
            4
            if indicators["volume_ratio"] >= 1.2 and indicators["change_5d"] > 0
            else -4
            if indicators["volume_ratio"] >= 1.2 and indicators["change_5d"] < 0
            else 0
        ),
        "range_position": float(
            5 if indicators["position_52w"] >= 0.7 else -5 if indicators["position_52w"] <= 0.3 else 0
        ),
        "roc": float(3 if indicators["roc_10"] > 0 else -3 if indicators["roc_10"] < 0 else 0),
    }
    return out
