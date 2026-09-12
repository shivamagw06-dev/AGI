"""FVL production facade."""

from __future__ import annotations

from typing import Any

from forecast_validation_learning.engine import ForecastValidationLearningEngine

_ENGINE = ForecastValidationLearningEngine()


def health() -> dict[str, Any]:
    return _ENGINE.health()


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def register(
    *,
    entity: str | None = None,
    scope: str = "company",
    question: str | None = None,
    assessment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if assessment:
        return _ENGINE.register_assessment(assessment)
    if not entity:
        raise ValueError("entity or assessment required")
    return _ENGINE.register_entity(entity, scope=scope, question=question)


def validate(
    forecast_id: str,
    *,
    actual_outcome: dict[str, Any] | None = None,
    generate_learning: bool = True,
) -> dict[str, Any]:
    return _ENGINE.validate(
        forecast_id,
        actual_override=actual_outcome,
        generate_learning_record=generate_learning,
    )


def validate_entity(
    entity: str,
    *,
    scope: str = "company",
    question: str | None = None,
    actual_outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _ENGINE.validate_entity(
        entity, scope=scope, question=question, actual_override=actual_outcome
    )


def get_validation(forecast_id: str) -> dict[str, Any]:
    return _ENGINE.get_validation(forecast_id)


def learning(*, limit: int = 50, category: str | None = None) -> dict[str, Any]:
    return _ENGINE.learning(limit=limit, category=category)


def performance(*, scope: str | None = None) -> dict[str, Any]:
    return _ENGINE.performance(scope=scope)


def calibration() -> dict[str, Any]:
    return _ENGINE.calibration()


def history(
    *,
    entity: str | None = None,
    scope: str = "company",
    limit: int = 50,
) -> dict[str, Any]:
    return _ENGINE.history(entity=entity, scope=scope, limit=limit)
