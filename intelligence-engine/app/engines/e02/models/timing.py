"""Factor timing / rotation placeholders — feature-flagged OFF for P0."""

from __future__ import annotations

from typing import Any


def timing_weights(e01_state: dict[str, Any]) -> dict[str, float]:
    raise RuntimeError("E02_TIMING is disabled for P0")


def rotation_state(universe_scores: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("E02_ROTATION is disabled for P0")
