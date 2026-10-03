"""Quality engine — authority, completeness, freshness, coverage, reliability."""

from __future__ import annotations

from typing import Any

from acquisition_planner.api_registry import PROVIDERS, provider_authority_score


def score_acquisition_quality(
    *,
    required_data: list[dict[str, Any]],
    acquire_steps: list[dict[str, Any]],
    reuse_steps: list[dict[str, Any]],
    freshness_plan: dict[str, Any],
) -> dict[str, Any]:
    covered = {str(s.get("evidence_key")) for s in acquire_steps + reuse_steps}
    needed = [str(r.get("evidence_key")) for r in required_data]
    completeness = (len(covered & set(needed)) / len(needed)) if needed else 1.0

    authority_scores = []
    reliability_scores = []
    for step in acquire_steps + reuse_steps:
        pid = str(step.get("provider") or "")
        meta = PROVIDERS.get(pid, {})
        authority_scores.append(provider_authority_score(pid) if pid in PROVIDERS else 0.5)
        reliability_scores.append(float(meta.get("reliability") or 0.7))

    authority = sum(authority_scores) / len(authority_scores) if authority_scores else 0.0
    reliability = sum(reliability_scores) / len(reliability_scores) if reliability_scores else 0.0
    # freshness: reuse + acquire both count; educational gets full credit
    req_f = freshness_plan.get("required_freshness")
    freshness = 0.95 if req_f in {"existing_knowledge", "quarterly", "daily"} else 0.9
    if req_f == "live" and any(s.get("evidence_key") == "live_prices" for s in acquire_steps):
        freshness = 0.97
    coverage = completeness

    overall = round(0.3 * authority + 0.25 * completeness + 0.2 * freshness + 0.15 * coverage + 0.1 * reliability, 4)
    return {
        "authority": round(authority, 4),
        "completeness": round(completeness, 4),
        "freshness": round(freshness, 4),
        "coverage": round(coverage, 4),
        "reliability": round(reliability, 4),
        "expected_quality": overall,
        "covered_evidence": sorted(covered),
        "uncovered_evidence": sorted(set(needed) - covered),
    }
