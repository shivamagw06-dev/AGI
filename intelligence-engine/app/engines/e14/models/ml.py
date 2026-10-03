"""ML / anomaly / SHAP placeholders — feature-flagged OFF for P0."""

from __future__ import annotations

from typing import Any


def infer_ml_risk(feature_vector: dict[str, float]) -> dict[str, Any] | None:
    raise RuntimeError("E14_ML is disabled for P0 — ML inference is not implemented")


def shap_explain(feature_vector: dict[str, float]) -> dict[str, Any] | None:
    raise RuntimeError("E14_ML is disabled for P0 — SHAP is not implemented")
