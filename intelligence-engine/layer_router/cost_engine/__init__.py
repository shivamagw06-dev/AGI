"""Estimate latency, cost units, API calls for the planned pipeline."""

from __future__ import annotations

from typing import Any

from layer_router.registry import LAYER_DEFS


def estimate_cost(
    required: list[str],
    optional: list[str],
    parallel_groups: list[dict[str, Any]],
) -> dict[str, Any]:
    run = list(required)  # cost plan focuses on required; optional noted separately
    serial_ms = sum(int((LAYER_DEFS.get(x) or {}).get("latency_ms") or 50) for x in run)
    cost_units = sum(int((LAYER_DEFS.get(x) or {}).get("cost_units") or 3) for x in run)
    # Parallel-aware runtime: sum of max latency per level among required members
    req_set = set(required)
    parallel_ms = 0
    for g in parallel_groups:
        members = [m for m in g.get("layers") or [] if m in req_set]
        if not members:
            continue
        parallel_ms += max(int((LAYER_DEFS.get(m) or {}).get("latency_ms") or 50) for m in members)
    if parallel_ms <= 0:
        parallel_ms = serial_ms

    baseline_all = sum(int((LAYER_DEFS.get(x) or {}).get("latency_ms") or 50) for x in LAYER_DEFS)
    reduction = round(1.0 - (parallel_ms / baseline_all), 4) if baseline_all else 0.0

    return {
        "estimated_runtime_ms": parallel_ms,
        "serial_runtime_ms": serial_ms,
        "baseline_all_layers_ms": baseline_all,
        "runtime_reduction": max(0.0, reduction),
        "expected_cost": {
            "cost_units": cost_units,
            "api_calls": len(run),
            "optional_api_calls": len(optional),
            "memory_units": round(cost_units * 1.2, 1),
            "token_estimate": cost_units * 400,
        },
        "layers_costed": run,
    }
