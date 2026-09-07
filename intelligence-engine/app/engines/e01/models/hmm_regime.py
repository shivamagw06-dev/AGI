"""HMM regime placeholder — feature-flagged OFF for P0 (E01_HMM=false)."""

from __future__ import annotations

from typing import Any


def infer_hmm_axis_posteriors(feature_vector: dict[str, float]) -> dict[str, Any] | None:
    """P2 placeholder. Must not be called when E01_HMM is false."""
    raise RuntimeError("E01_HMM is disabled for P0 — HMM inference is not implemented")
