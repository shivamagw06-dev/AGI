"""ML / smart-beta placeholders — feature-flagged OFF for P0."""

from __future__ import annotations

from typing import Any


def ml_factor_scores(panel: dict[str, float]) -> dict[str, Any]:
    raise RuntimeError("E02_ML is disabled for P0")


def smart_beta_weights(exposures: dict[str, float]) -> dict[str, Any]:
    raise RuntimeError("E02_SMART_BETA is disabled for P0")
