"""CRE dashboard payload — trends, rankings, confidence/performance, promotion readiness."""

from __future__ import annotations

from typing import Any

from app.cre.models import (
    CREEvaluationResult,
    CompositeScorecard,
    EngineScorecard,
    PromotionReport,
)
from app.validation.models import ReplayDaySlice


def build_cre_dashboard(
    *,
    days: list[ReplayDaySlice],
    scorecards: list[EngineScorecard],
    composite: CompositeScorecard | None,
    promotion: PromotionReport | None,
    series: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Assemble CRE dashboard sections (evaluation only)."""
    confidence_trends = [
        {
            "as_of": d.as_of,
            "mean_confidence": round(
                sum(d.confidences.values()) / len(d.confidences), 6
            )
            if d.confidences
            else None,
            "n": len(d.confidences),
        }
        for d in days
    ]
    performance_trends = [
        {
            "as_of": d.as_of,
            "portfolio_return": d.portfolio_return,
            "benchmark_return": d.benchmark_return,
            "n_positions": len(d.portfolio_weights),
            "cash_allocation": d.cash_allocation,
        }
        for d in days
    ]
    engine_rankings = [
        {
            "engine": s.engine,
            "rank_score": s.rank_score,
            "status": s.status,
            "model_version": s.model_version,
            "rolling_30_ic": (
                s.rolling["30"].information_coefficient if "30" in s.rolling else None
            ),
            "rolling_90_ic": (
                s.rolling["90"].information_coefficient if "90" in s.rolling else None
            ),
            "rolling_252_ic": (
                s.rolling["252"].information_coefficient if "252" in s.rolling else None
            ),
        }
        for s in sorted(scorecards, key=lambda x: (-x.rank_score, x.engine))
    ]
    trend_charts = {
        "confidence": confidence_trends,
        "performance": performance_trends,
        "rank_scores": [
            {"engine": s.engine, "rank_score": s.rank_score} for s in scorecards
        ],
        "rolling_hit_rate": [
            {
                "engine": s.engine,
                "w30": s.rolling["30"].hit_rate if "30" in s.rolling else None,
                "w90": s.rolling["90"].hit_rate if "90" in s.rolling else None,
                "w252": s.rolling["252"].hit_rate if "252" in s.rolling else None,
            }
            for s in scorecards
        ],
    }
    promotion_readiness = {
        "ready": False if promotion is None else promotion.ready,
        "evidence_only": True if promotion is None else promotion.evidence_only,
        "promotion_flag": False if promotion is None else promotion.promotion_flag,
        "engine": None if promotion is None else promotion.engine,
        "blocking_reasons": [] if promotion is None else promotion.blocking_reasons,
        "checklist": [] if promotion is None else promotion.checklist,
    }
    return {
        "trend_charts": trend_charts,
        "engine_rankings": engine_rankings,
        "confidence_trends": confidence_trends,
        "performance_trends": performance_trends,
        "promotion_readiness": promotion_readiness,
        "composite": composite.model_dump(mode="json") if composite else None,
        "series": series or {},
        "windows": [30, 90, 252],
    }


def dashboard_from_result(
    result: CREEvaluationResult,
    series: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return result.dashboard if result.dashboard else {
        "trend_charts": {},
        "engine_rankings": [],
        "confidence_trends": [],
        "performance_trends": [],
        "promotion_readiness": {"ready": False, "evidence_only": True},
        "composite": result.composite.model_dump(mode="json") if result.composite else None,
        "series": series or {},
        "windows": [30, 90, 252],
    }
