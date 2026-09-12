"""ML placeholder — feature-flagged OFF for P0 (E01_ML=false)."""

from __future__ import annotations

from typing import Any


def infer_ml_axis_labels(feature_vector: dict[str, float]) -> dict[str, Any] | None:
    """Future supervised axis classifiers. Must not run when E01_ML is false."""
    raise RuntimeError("E01_ML is disabled for P0 — ML inference is not implemented")
