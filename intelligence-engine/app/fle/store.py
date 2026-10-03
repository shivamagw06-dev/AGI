"""FLE store — immutable forecast append log; soft-delete only; never overwrite."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.fle.models import (
    AccuracySummary,
    AuditEntry,
    CalibrationSnapshot,
    ForecastHealth,
    ForecastRecord,
    LearningRecord,
    OutcomeRecord,
    RelationshipEdge,
    now_iso,
)


@dataclass
class FleMetrics:
    forecasts_created: int = 0
    forecasts_resolved: int = 0
    average_accuracy: float = 0.0
    calibration_drift: float = 0.0
    forecast_latency_ms: float = 0.0
    pending_reviews: int = 0
    learning_objects_generated: int = 0
    forecast_failures: int = 0
    resolution_queue: int = 0

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {
            "forecasts_created": self.forecasts_created,
            "forecasts_resolved": self.forecasts_resolved,
            "average_accuracy": self.average_accuracy,
            "calibration_drift": self.calibration_drift,
            "forecast_latency_ms": self.forecast_latency_ms,
            "pending_reviews": self.pending_reviews,
            "learning_objects_generated": self.learning_objects_generated,
            "forecast_failures": self.forecast_failures,
            "resolution_queue": self.resolution_queue,
        }


class FleStore:
    def __init__(self) -> None:
        self.forecasts: dict[str, ForecastRecord] = {}  # immutable by id
        self.forecast_versions: list[str] = []  # ordered forecast_ids including superseded
        self.outcomes: dict[str, OutcomeRecord] = {}  # by forecast_id
        self.learnings: dict[str, LearningRecord] = {}  # by learning_id
        self.calibration_history: list[CalibrationSnapshot] = []
        self.accuracy: dict[str, AccuracySummary] = {}  # scope|scope_id
        self.health: dict[str, ForecastHealth] = {}
        self.relationships: dict[str, RelationshipEdge] = {}
        self.audit: list[AuditEntry] = []
        self.metrics = FleMetrics()

    def add_forecast(self, forecast: ForecastRecord) -> ForecastRecord:
        # Immutable: never overwrite existing forecast_id
        if forecast.forecast_id in self.forecasts:
            return self.forecasts[forecast.forecast_id]
        self.forecasts[forecast.forecast_id] = forecast
        self.forecast_versions.append(forecast.forecast_id)
        self.metrics.forecasts_created = len(self.forecasts)
        self._refresh_pending()
        self.audit_event("add_forecast", object_kind="forecast", object_id=forecast.forecast_id)
        return forecast

    def mark_superseded(self, forecast_id: str) -> None:
        fc = self.forecasts.get(forecast_id)
        if not fc or fc.soft_deleted:
            return
        # Replace with copy status change only via new object identity pattern:
        # For immutability of analytical content we allow status transition fields only.
        fc.status = "superseded"
        self.audit_event("supersede_forecast", object_kind="forecast", object_id=forecast_id)

    def soft_delete_forecast(self, forecast_id: str) -> bool:
        fc = self.forecasts.get(forecast_id)
        if not fc or fc.soft_deleted:
            return False
        fc.soft_deleted = True
        fc.status = "expired"
        self.audit_event("soft_delete_forecast", object_kind="forecast", object_id=forecast_id)
        self._refresh_pending()
        return True

    def active_forecasts(
        self,
        *,
        company_id: str | None = None,
        sector_id: str | None = None,
        metric: str | None = None,
        status: str | None = None,
    ) -> list[ForecastRecord]:
        rows = [f for f in self.forecasts.values() if not f.soft_deleted]
        if company_id:
            rows = [f for f in rows if f.company_id == company_id or f.company_symbol == company_id]
        if sector_id:
            rows = [f for f in rows if f.sector_id == sector_id]
        if metric:
            rows = [f for f in rows if f.metric == metric]
        if status:
            rows = [f for f in rows if f.status == status]
        return rows

    def add_outcome(self, outcome: OutcomeRecord) -> OutcomeRecord:
        # One outcome per forecast; do not overwrite — skip if exists
        if outcome.forecast_id in self.outcomes:
            return self.outcomes[outcome.forecast_id]
        self.outcomes[outcome.forecast_id] = outcome
        fc = self.forecasts.get(outcome.forecast_id)
        if fc:
            fc.status = "resolved"
        self.metrics.forecasts_resolved = len(self.outcomes)
        self._refresh_pending()
        self.audit_event("add_outcome", object_kind="outcome", object_id=outcome.outcome_id)
        return outcome

    def add_learning(self, learning: LearningRecord) -> LearningRecord:
        if learning.learning_id in self.learnings:
            return self.learnings[learning.learning_id]
        self.learnings[learning.learning_id] = learning
        self.metrics.learning_objects_generated = len(self.learnings)
        self.audit_event("add_learning", object_kind="learning", object_id=learning.learning_id)
        return learning

    def add_calibration(self, snap: CalibrationSnapshot) -> None:
        self.calibration_history.append(snap)
        self.metrics.calibration_drift = snap.calibration_drift

    def put_accuracy(self, summary: AccuracySummary) -> None:
        key = f"{summary.scope}|{summary.scope_id}"
        self.accuracy[key] = summary
        if summary.scope == "global":
            self.metrics.average_accuracy = summary.mean_accuracy_score

    def put_health(self, health: ForecastHealth) -> None:
        self.health[health.company_id] = health

    def add_relationship(self, edge: RelationshipEdge) -> None:
        key = f"{edge.from_id}|{edge.relation_type}|{edge.to_id}"
        self.relationships[key] = edge

    def audit_event(self, action: str, *, object_kind: str = "", object_id: str = "", detail: str = "") -> None:
        self.audit.append(
            AuditEntry(action=action, object_kind=object_kind, object_id=object_id, detail=detail)
        )

    def _refresh_pending(self) -> None:
        pending = [
            f
            for f in self.forecasts.values()
            if not f.soft_deleted and f.status in {"active", "pending", "review_due"}
        ]
        self.metrics.pending_reviews = len([f for f in pending if f.status == "review_due"])
        self.metrics.resolution_queue = len(pending)

    def snapshot(self) -> dict[str, Any]:
        return {
            "forecasts": len(self.forecasts),
            "active_forecasts": len(self.active_forecasts()),
            "outcomes": len(self.outcomes),
            "learnings": len(self.learnings),
            "calibration_snapshots": len(self.calibration_history),
            "accuracy_scopes": len(self.accuracy),
            "health": len(self.health),
            "relationships": len(self.relationships),
            "audit": len(self.audit),
        }

    def history_for_company(self, company_id: str) -> list[ForecastRecord]:
        rows = [
            f
            for f in self.forecasts.values()
            if f.company_id == company_id or f.company_symbol == company_id
        ]
        return sorted(rows, key=lambda f: f.created_at, reverse=True)
