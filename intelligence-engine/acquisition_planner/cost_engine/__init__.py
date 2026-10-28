"""Cost engine — provider acquisition cost accounting."""

from __future__ import annotations

from typing import Any

from acquisition_planner.api_registry import PROVIDERS


def score_costs(acquire_steps: list[dict[str, Any]], reuse_steps: list[dict[str, Any]]) -> dict[str, Any]:
    api_cost = 0
    runtime_ms = 0.0
    rows = []
    for step in acquire_steps:
        pid = str(step.get("provider") or "")
        meta = PROVIDERS.get(pid, {})
        cost = int(meta.get("cost") or step.get("cost") or 1)
        lat = float(meta.get("latency_ms") or step.get("expected_latency_ms") or 100)
        api_cost += cost
        runtime_ms += lat
        rows.append(
            {
                "provider": pid,
                "cost": cost,
                "expected_value": step.get("expected_value") or ("Very High" if meta.get("tier", 5) <= 1 else "High" if meta.get("tier", 5) <= 2 else "Medium"),
                "latency_ms": lat,
            }
        )
    reuse_value = len(reuse_steps)  # free evidence units
    return {
        "api_call_cost": api_cost,
        "expected_runtime_ms": round(runtime_ms, 2),
        "reuse_free_units": reuse_value,
        "cost_rows": rows,
        "naive_external_calls_if_all_fetched": api_cost + reuse_value,
    }
