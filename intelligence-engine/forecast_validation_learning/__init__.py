"""Forecast Validation & Learning (FVL) — Sprint 9.5.

Compares registered forecasts with actual outcomes, scores quality,
detects biases, tracks calibration, and generates institutional learning
without rewriting historical forecasts.
"""

from forecast_validation_learning.engine import ForecastValidationLearningEngine

__all__ = ["ForecastValidationLearningEngine"]
