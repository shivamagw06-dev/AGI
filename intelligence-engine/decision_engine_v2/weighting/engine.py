"""Transparent dynamic weighting across institutional dimensions."""

from __future__ import annotations

import hashlib
from typing import Any

from decision_engine_v2.schema import WEIGHT_DIMENSIONS


def _seed(ticker: str, question: str) -> int:
    return int(hashlib.sha256(f"{ticker}|{question}".encode()).hexdigest()[:12], 16)


def compute_weights(
    inputs: dict[str, Any],
    *,
    question: str | None = None,
) -> dict[str, Any]:
    """Dynamic but reproducible weights; always sum to 1.0 and remain transparent."""
    t = inputs.get("ticker") or ""
    q = question or inputs.get("question") or ""
    layers = inputs.get("layers") or {}
    summary = inputs.get("stack_summary") or {}

    base = {d: 1.0 / len(WEIGHT_DIMENSIONS) for d in WEIGHT_DIMENSIONS}
    # Soft boosts from available signals (not opaque ML)
    if (layers.get("management_intelligence") or {}).get("confidence") is not None:
        base["management"] += 0.04
    if (layers.get("accounting_intelligence") or {}).get("confidence") is not None:
        base["accounting"] += 0.04
    if summary.get("forecast_most_likely") or (layers.get("forecast_intelligence") or {}).get("most_likely"):
        base["forecast"] += 0.05
    if summary.get("memory_lesson_count") or (layers.get("institutional_memory") or {}).get("lesson_count"):
        base["learning"] += 0.04
    if summary.get("portfolio_net_effect") or (layers.get("portfolio_intelligence") or {}).get("portfolio_quality") is not None:
        base["portfolio"] += 0.05
    if summary.get("causal_why") or (layers.get("causal_intelligence") or {}).get("confidence") is not None:
        base["macro"] += 0.03
    if (layers.get("peer_intelligence") or {}).get("enabled"):
        base["business"] += 0.03
    if (layers.get("simulation_lab") or {}).get("expected_return") is not None:
        base["risk"] += 0.03
    if (layers.get("evidence_intelligence") or {}).get("enabled", True):
        base["evidence"] += 0.04
    if (layers.get("accounting_intelligence") or {}).get("accounting_quality_score") is not None:
        base["financial"] += 0.03
    if (layers.get("forecast_intelligence") or {}).get("confidence") is not None:
        base["valuation"] += 0.02

    # Tiny deterministic jitter from seed so weights are question-sensitive but reproducible
    rng_seed = _seed(str(t), str(q))
    for i, dim in enumerate(WEIGHT_DIMENSIONS):
        nudge = ((rng_seed >> (i * 3)) & 7) / 1000.0
        base[dim] += nudge

    total = sum(base.values()) or 1.0
    weights = {k: round(v / total, 4) for k, v in base.items()}
    # Fix rounding drift
    drift = round(1.0 - sum(weights.values()), 4)
    weights["evidence"] = round(weights["evidence"] + drift, 4)
    return {
        "weights": weights,
        "sum": round(sum(weights.values()), 4),
        "transparent": True,
        "reproducible": True,
        "seed": rng_seed,
        "dimensions": list(WEIGHT_DIMENSIONS),
        "rule": "Weights are transparent and reproducible from ticker + question + soft signals",
    }
