"""Evidence Budget — optimise quality vs latency vs API spend."""

from __future__ import annotations

from typing import Any

from acquisition_planner.api_registry import PROVIDERS
from acquisition_planner.schema import DEFAULT_EVIDENCE_BUDGET


def resolve_budget(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    budget = dict(DEFAULT_EVIDENCE_BUDGET)
    if overrides:
        for k, v in overrides.items():
            if k in budget and v is not None:
                budget[k] = v
    return budget


def apply_evidence_budget(
    *,
    acquire_candidates: list[dict[str, Any]],
    reuse_steps: list[dict[str, Any]],
    budget: dict[str, Any],
    quality_preview: float,
) -> dict[str, Any]:
    """Select a subset of acquire steps that maximises value under budget."""
    max_runtime_ms = float(budget.get("maximum_runtime_ms") or 4000)
    max_api = int(budget.get("maximum_api_calls") or 8)
    target_conf = float(budget.get("target_confidence") or 0.9)
    min_tier = int(budget.get("minimum_authority_tier") or 2)

    # Score each candidate: expected value / cost
    scored = []
    for step in acquire_candidates:
        pid = str(step.get("provider") or "")
        meta = PROVIDERS.get(pid, {})
        tier = int(meta.get("tier") or step.get("tier") or 5)
        if tier > min_tier:
            continue
        cost = int(meta.get("cost") or step.get("cost") or 1)
        lat = float(meta.get("latency_ms") or step.get("expected_latency_ms") or 100)
        authority = float(step.get("authority_score") or (1.1 - 0.15 * tier))
        value = authority * 10 + (5 if tier <= 1 else 3 if tier <= 2 else 1)
        scored.append({**step, "cost": cost, "latency_ms": lat, "value": value, "value_per_cost": value / max(cost, 1)})

    scored.sort(key=lambda s: (-s["value_per_cost"], s["latency_ms"], s["cost"]))

    selected: list[dict[str, Any]] = []
    skipped_budget: list[dict[str, Any]] = []
    total_cost = 0
    total_lat = 0.0
    covered = {str(r.get("evidence_key")) for r in reuse_steps}

    for step in scored:
        key = str(step.get("evidence_key") or "")
        if key in covered:
            skipped_budget.append({**step, "skip_reason": "Already covered"})
            continue
        if len(selected) >= max_api:
            skipped_budget.append({**step, "skip_reason": "API call budget exhausted"})
            continue
        if total_lat + step["latency_ms"] > max_runtime_ms and selected:
            skipped_budget.append({**step, "skip_reason": "Runtime budget would be exceeded"})
            continue
        selected.append(step)
        covered.add(key)
        total_cost += step["cost"]
        total_lat += step["latency_ms"]

    # Estimate confidence after budget trim
    est_conf = min(0.99, quality_preview * 0.85 + 0.05 * len(reuse_steps) + 0.03 * len(selected))
    return {
        "budget": budget,
        "selected_acquire": selected,
        "skipped_for_budget": skipped_budget,
        "api_calls_used": len(selected),
        "runtime_ms_used": round(total_lat, 2),
        "api_cost_used": total_cost,
        "within_budget": len(selected) <= max_api and total_lat <= max_runtime_ms,
        "target_confidence": target_conf,
        "estimated_confidence_vs_target": round(est_conf, 4),
        "meets_target_confidence": est_conf >= target_conf or (len(selected) + len(reuse_steps)) >= 3,
        "optimisation": {
            "maximise": ["evidence_quality", "confidence", "internal_reuse"],
            "minimise": ["latency", "redundant_api_calls", "cost"],
        },
    }
