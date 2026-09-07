"""Materiality — escalate sector learning only on material outlook / event shifts."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import MaterialityTier, SectorKnowledgeObject
from continuous_sector_knowledge.store import STORE


def evaluate_materiality(sko: SectorKnowledgeObject) -> dict[str, Any]:
    prior = STORE.latest(sko.sector_key)
    tier: MaterialityTier = "Low"
    score = 0.2
    reason = "routine_sector_refresh"
    learn = False

    # First publication
    if prior is None:
        return _result(sko, "Medium", 0.55, "initial_sector_publication", True)

    outlook_changed = prior.current_outlook != sko.current_outlook
    trend_changed = (
        prior.revenue_trend != sko.revenue_trend or prior.margin_trend != sko.margin_trend
    )

    if sko.trigger == "macro_change" and outlook_changed:
        return _result(sko, "Critical", 0.92, "macro_driven_outlook_shift", True)
    if sko.trigger == "macro_change":
        return _result(sko, "High", 0.78, "macro_driven_sector_refresh", True)
    if sko.trigger == "earnings" and (outlook_changed or trend_changed):
        return _result(sko, "High", 0.80, "earnings_season_outlook_shift", True)
    if sko.trigger == "ma":
        return _result(sko, "Medium", 0.60, "competitive_dynamics_update", True)
    if outlook_changed:
        return _result(sko, "High", 0.75, "outlook_changed", True)
    if trend_changed:
        return _result(sko, "Medium", 0.55, "trend_changed", True)

    # Identical refresh — publish knowledge, skip learning
    if (
        prior.current_outlook == sko.current_outlook
        and prior.revenue_trend == sko.revenue_trend
        and prior.margin_trend == sko.margin_trend
        and prior.valuation == sko.valuation
    ):
        return _result(sko, "Ignore", 0.0, "sector_unchanged", False)

    return _result(sko, tier, score, reason, learn)


def _result(
    sko: SectorKnowledgeObject,
    tier: MaterialityTier,
    score: float,
    reason: str,
    learn: bool,
) -> dict[str, Any]:
    sko.materiality_tier = tier
    sko.materiality_score = score
    return {
        "tier": tier,
        "score": score,
        "reason": reason,
        "learn": learn,
        "filtered": tier == "Ignore",
        "sector_key": sko.sector_key,
    }
