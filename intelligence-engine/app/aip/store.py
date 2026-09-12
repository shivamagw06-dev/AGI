"""AIP store — experiment / report history only (no production writes)."""

from __future__ import annotations

import threading
from typing import Any

from app.aip.models import (
    AttributionReport,
    CalibrationPlan,
    ContributionReport,
    ExperimentResult,
    PromotionEvidence,
)


class AipStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._experiments: dict[str, ExperimentResult] = {}
        self._order: list[str] = []
        self._latest_id: str | None = None
        self._contribution: ContributionReport | None = None
        self._calibration: CalibrationPlan | None = None
        self._attribution: AttributionReport | None = None
        self._promotion: PromotionEvidence | None = None

    def put_experiment(self, result: ExperimentResult) -> None:
        with self._lock:
            self._experiments[result.experiment_id] = result
            if result.experiment_id not in self._order:
                self._order.append(result.experiment_id)
            self._latest_id = result.experiment_id
            if result.contribution is not None:
                self._contribution = result.contribution
            if result.calibration is not None:
                self._calibration = result.calibration
            if result.attribution is not None:
                self._attribution = result.attribution

    def get_experiment(self, experiment_id: str) -> ExperimentResult | None:
        with self._lock:
            return self._experiments.get(experiment_id)

    def latest(self) -> ExperimentResult | None:
        with self._lock:
            if self._latest_id is None:
                return None
            return self._experiments.get(self._latest_id)

    def list_experiments(self, limit: int = 50) -> list[ExperimentResult]:
        with self._lock:
            ids = list(reversed(self._order[-limit:]))
            return [self._experiments[i] for i in ids if i in self._experiments]

    def put_promotion(self, evidence: PromotionEvidence) -> None:
        with self._lock:
            self._promotion = evidence

    def get_promotion(self) -> PromotionEvidence | None:
        with self._lock:
            return self._promotion

    def get_contribution(self) -> ContributionReport | None:
        with self._lock:
            return self._contribution

    def get_calibration(self) -> CalibrationPlan | None:
        with self._lock:
            return self._calibration

    def get_attribution(self) -> AttributionReport | None:
        with self._lock:
            return self._attribution

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "n_experiments": len(self._experiments),
                "latest_experiment_id": self._latest_id,
                "has_contribution": self._contribution is not None,
                "has_calibration": self._calibration is not None,
                "has_attribution": self._attribution is not None,
                "promotion_ready": bool(self._promotion.ready) if self._promotion else False,
            }
