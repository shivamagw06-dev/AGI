"""CRE platform service facade (CRE-001–005)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.cre.flags import CREFlags
from app.cre.models import (
    CREEvaluationResult,
    CompositeScorecard,
    EngineScorecard,
    PromotionReport,
)
from app.cre.runner import DailyEvaluationRunner
from app.cre.store import CREStore
from app.validation.golden.loader import GoldenDataset


class CREService:
    """Continuous Research Evaluation — no production influence, evidence-only promotion."""

    def __init__(
        self,
        store: CREStore | None = None,
        flags: CREFlags | None = None,
    ) -> None:
        self.flags = flags or CREFlags.from_settings()
        self.store = store or CREStore()
        self.runner = DailyEvaluationRunner(store=self.store, flags=self.flags)

    def evaluate(
        self,
        dataset_id: str = "golden_p0_v1",
        *,
        dataset: GoldenDataset | None = None,
        generated_at: datetime | None = None,
    ) -> CREEvaluationResult:
        return self.runner.run(dataset_id, dataset=dataset, generated_at=generated_at)

    def latest(self) -> CREEvaluationResult | None:
        return self.store.latest()

    def get_evaluation(self, evaluation_id: str) -> CREEvaluationResult | None:
        return self.store.get_evaluation(evaluation_id)

    def list_evaluations(self, limit: int = 50) -> list[CREEvaluationResult]:
        return self.store.list_evaluations(limit=limit)

    def list_scorecards(self) -> list[EngineScorecard]:
        return self.store.list_scorecards()

    def get_scorecard(self, engine: str) -> EngineScorecard | None:
        return self.store.get_scorecard(engine)

    def get_composite(self) -> CompositeScorecard | None:
        return self.store.get_composite()

    def get_alerts(self) -> dict[str, list[Any]]:
        return self.store.get_alerts()

    def get_promotion(self) -> PromotionReport | None:
        return self.store.get_promotion()

    def get_dashboard(self) -> dict[str, Any] | None:
        latest = self.store.latest()
        if latest is None:
            return None
        return latest.dashboard

    def health(self) -> dict[str, Any]:
        return self.runner.health()
