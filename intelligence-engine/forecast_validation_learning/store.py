"""In-process FVL stores — registry, validations, learnings (append-only)."""

from __future__ import annotations

import copy
import time
from typing import Any

from forecast_validation_learning.schema import (
    ForecastValidation,
    InvestmentLearning,
    RegisteredForecast,
    TERMINAL_STATUSES,
)


class ForecastRegistry:
    """Immutable forecast registry. Snapshots are never mutated in place.

    Current lifecycle status is tracked in a side index + append-only log so
    the registered assessment snapshot / expected outcome never change.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, RegisteredForecast] = {}
        self._versions: dict[str, list[str]] = {}  # entity key -> forecast_ids
        self._status: dict[str, str] = {}
        self._status_log: list[dict[str, Any]] = []

    def register(self, forecast: RegisteredForecast) -> RegisteredForecast:
        if forecast.forecast_id in self._by_id:
            raise ValueError(f"forecast_id already registered (immutable): {forecast.forecast_id}")
        frozen = RegisteredForecast.model_validate(copy.deepcopy(forecast.model_dump(mode="json")))
        self._by_id[frozen.forecast_id] = frozen
        self._status[frozen.forecast_id] = frozen.status
        key = f"{frozen.scope}:{frozen.entity}".upper()
        self._versions.setdefault(key, []).append(frozen.forecast_id)
        self._status_log.append(
            {
                "forecast_id": frozen.forecast_id,
                "status": frozen.status,
                "ts": time.time(),
                "event": "registered",
            }
        )
        return frozen

    def get(self, forecast_id: str) -> RegisteredForecast | None:
        return self._by_id.get(forecast_id)

    def current_status(self, forecast_id: str) -> str | None:
        return self._status.get(forecast_id)

    def record_status(self, forecast_id: str, status: str, *, event: str = "status") -> None:
        if forecast_id not in self._by_id:
            raise KeyError(forecast_id)
        self._status[forecast_id] = status
        self._status_log.append(
            {
                "forecast_id": forecast_id,
                "status": status,
                "ts": time.time(),
                "event": event,
                "terminal": status in TERMINAL_STATUSES,
            }
        )

    def public_view(self, forecast: RegisteredForecast) -> dict[str, Any]:
        data = forecast.to_public_dict()
        data["status"] = self._status.get(forecast.forecast_id, forecast.status)
        data["status_is_lifecycle_pointer"] = True
        data["snapshot_body_immutable"] = True
        return data

    def list_all(self, *, limit: int = 100) -> list[RegisteredForecast]:
        rows = list(self._by_id.values())
        rows.sort(key=lambda r: r.forecast_date, reverse=True)
        return rows[:limit]

    def list_for_entity(
        self, entity: str, *, scope: str = "company", limit: int = 50
    ) -> list[RegisteredForecast]:
        key = f"{scope}:{entity}".upper()
        ids = self._versions.get(key) or []
        out = [self._by_id[i] for i in reversed(ids) if i in self._by_id]
        return out[:limit]

    def status_log(self, limit: int = 100) -> list[dict[str, Any]]:
        return list(reversed(self._status_log[-limit:]))

    def counts_by_status(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self._status.values():
            out[s] = out.get(s, 0) + 1
        return out

    def clear(self) -> None:
        self._by_id.clear()
        self._versions.clear()
        self._status.clear()
        self._status_log.clear()


class ValidationStore:
    def __init__(self) -> None:
        self._by_id: dict[str, ForecastValidation] = {}
        self._by_forecast: dict[str, list[str]] = {}

    def append(self, validation: ForecastValidation) -> ForecastValidation:
        if validation.validation_id in self._by_id:
            raise ValueError(f"validation_id already exists (immutable): {validation.validation_id}")
        frozen = ForecastValidation.model_validate(copy.deepcopy(validation.model_dump(mode="json")))
        self._by_id[frozen.validation_id] = frozen
        self._by_forecast.setdefault(frozen.forecast_id, []).append(frozen.validation_id)
        return frozen

    def get(self, validation_id: str) -> ForecastValidation | None:
        return self._by_id.get(validation_id)

    def for_forecast(self, forecast_id: str) -> list[ForecastValidation]:
        ids = self._by_forecast.get(forecast_id) or []
        return [self._by_id[i] for i in ids if i in self._by_id]

    def list_all(self, *, limit: int = 100) -> list[ForecastValidation]:
        rows = list(self._by_id.values())
        rows.sort(key=lambda r: r.validation_date, reverse=True)
        return rows[:limit]

    def clear(self) -> None:
        self._by_id.clear()
        self._by_forecast.clear()


class LearningStore:
    def __init__(self) -> None:
        self._rows: list[InvestmentLearning] = []

    def append(self, learning: InvestmentLearning) -> InvestmentLearning:
        frozen = InvestmentLearning.model_validate(copy.deepcopy(learning.model_dump(mode="json")))
        self._rows.append(frozen)
        if len(self._rows) > 1000:
            del self._rows[:-1000]
        return frozen

    def list_all(self, *, limit: int = 100, category: str | None = None) -> list[InvestmentLearning]:
        rows = list(reversed(self._rows))
        if category:
            rows = [r for r in rows if r.category == category]
        return rows[:limit]

    def clear(self) -> None:
        self._rows.clear()


class MetricsStore:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def record(self, row: dict[str, Any]) -> None:
        self._events.append({**row, "ts": time.time()})
        if len(self._events) > 500:
            del self._events[:-500]

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._events[-limit:]))

    def clear(self) -> None:
        self._events.clear()


REGISTRY = ForecastRegistry()
VALIDATIONS = ValidationStore()
LEARNINGS = LearningStore()
METRICS = MetricsStore()


def reset_all() -> None:
    REGISTRY.clear()
    VALIDATIONS.clear()
    LEARNINGS.clear()
    METRICS.clear()
