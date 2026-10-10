"""Bayesian updating placeholder — feature-flagged OFF for P0."""

from __future__ import annotations

from typing import Any


def bayesian_update(prior: dict[str, float], evidence: dict[str, float]) -> dict[str, Any] | None:
    raise RuntimeError("E14_BAYES is disabled for P0 — Bayesian models are not implemented")
