"""CRE-002 Rolling Metrics Store — evaluation history only (no production writes)."""

from __future__ import annotations

import threading
from typing import Any

from app.cre.models import (
    CREEvaluationResult,
    CompositeScorecard,
    DriftAlert,
    EngineScorecard,
    PromotionReport,
    RegressionAlert,
)


class CREStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._evaluations: dict[str, CREEvaluationResult] = {}
        self._order: list[str] = []
        self._latest_id: str | None = None
        self._scorecards: dict[str, EngineScorecard] = {}  # engine -> latest
        self._composite: CompositeScorecard | None = None
        self._drift: list[DriftAlert] = []
        self._regression: list[RegressionAlert] = []
        self._promotion: PromotionReport | None = None
        # Rolling series points for charts: engine -> list[{as_of, metrics...}]
        self._series: dict[str, list[dict[str, Any]]] = {}

    def put(self, result: CREEvaluationResult) -> None:
        with self._lock:
            self._evaluations[result.evaluation_id] = result
            if result.evaluation_id not in self._order:
                self._order.append(result.evaluation_id)
            self._latest_id = result.evaluation_id
            for sc in result.engine_scorecards:
                self._scorecards[sc.engine] = sc
                series = self._series.setdefault(sc.engine, [])
                point = {
                    "as_of": sc.as_of,
                    "rank_score": sc.rank_score,
                    "status": sc.status,
                    "rolling_30": sc.rolling.get("30").model_dump(mode="json") if "30" in sc.rolling else None,
                }
                series[:] = [p for p in series if p["as_of"] != sc.as_of]
                series.append(point)
                series.sort(key=lambda p: p["as_of"])
            self._composite = result.composite
            self._drift = list(result.drift_alerts)
            self._regression = list(result.regression_alerts)
            self._promotion = result.promotion

    def get_evaluation(self, evaluation_id: str) -> CREEvaluationResult | None:
        with self._lock:
            return self._evaluations.get(evaluation_id)

    def latest(self) -> CREEvaluationResult | None:
        with self._lock:
            if self._latest_id is None:
                return None
            return self._evaluations.get(self._latest_id)

    def list_evaluations(self, limit: int = 50) -> list[CREEvaluationResult]:
        with self._lock:
            ids = list(reversed(self._order[-limit:]))
            return [self._evaluations[i] for i in ids if i in self._evaluations]

    def get_scorecard(self, engine: str) -> EngineScorecard | None:
        with self._lock:
            return self._scorecards.get(engine.upper())

    def list_scorecards(self) -> list[EngineScorecard]:
        with self._lock:
            return list(self._scorecards.values())

    def get_composite(self) -> CompositeScorecard | None:
        with self._lock:
            return self._composite

    def get_alerts(self) -> dict[str, list[Any]]:
        with self._lock:
            return {
                "drift": [a.model_dump(mode="json") for a in self._drift],
                "regression": [a.model_dump(mode="json") for a in self._regression],
            }

    def get_promotion(self) -> PromotionReport | None:
        with self._lock:
            return self._promotion

    def series(self, engine: str | None = None) -> dict[str, list[dict[str, Any]]]:
        with self._lock:
            if engine:
                return {engine.upper(): list(self._series.get(engine.upper(), []))}
            return {k: list(v) for k, v in self._series.items()}

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "evaluations": len(self._evaluations),
                "scorecards": len(self._scorecards),
                "drift_alerts": len(self._drift),
                "regression_alerts": len(self._regression),
                "schema": "cre_replay",
            }
