"""Observability board — pipeline health, queues, failures, freshness, cache proxies."""

from __future__ import annotations

from typing import Any

from production_hardening.util import now_iso, soft_call


def build_observability_board(
    *,
    gold_result: dict[str, Any] | None = None,
    scale_result: dict[str, Any] | None = None,
    dq_result: dict[str, Any] | None = None,
    perf_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    oie_h = soft_call("opportunity_intelligence", _health_oie)
    kde_h = soft_call("knowledge_delta", _health_kde)
    iol_h = soft_call("investment_operations", _health_iol)
    aro_h = soft_call("autonomous_research", _health_aro)
    obs_h = soft_call("observability", _health_obs)
    mc_h = soft_call("mission_control", _health_mc)

    pipeline = [
        _pipe("company_memory/knowledge_delta", kde_h),
        _pipe("opportunity_intelligence", oie_h),
        _pipe("investment_operations", iol_h),
        _pipe("autonomous_research", aro_h),
        _pipe("observability", obs_h),
        _pipe("mission_control", mc_h),
    ]

    # Queue lengths come from latest scale/gold/dq runs — avoid re-running full ARO/IOL desks here
    queues = {
        "gold_universe_n": len((gold_result or {}).get("universe") or []) or None,
        "scale_universe_n": (scale_result or {}).get("n"),
        "dq_failures_n": len((dq_result or {}).get("failures") or []),
        "scale_fail_n": (scale_result or {}).get("fail_n"),
        "note": "Full ARO/IOL queue depths available via /v1/autonomous-research/status and /v1/investment-operations/metrics",
    }

    failures = {
        "scale_fail_n": (scale_result or {}).get("fail_n"),
        "scale_errors": ((scale_result or {}).get("errors") or [])[:10],
        "gold_mismatches_n": len((gold_result or {}).get("mismatches") or []),
        "dq_failures_n": len((dq_result or {}).get("failures") or []),
    }

    processing = {
        "scale_elapsed_s": (scale_result or {}).get("elapsed_s"),
        "scale_throughput_per_min": (scale_result or {}).get("throughput_per_min"),
        "scale_latency_ms": (scale_result or {}).get("latency_ms"),
        "perf_profiles": (perf_result or {}).get("profiles"),
    }

    cache = {
        "note": "Cache hit proxy = memory_cache hits during DQ (compiled intelligence, not raw APIs)",
        "memory_cache_hit_rate_pct": (dq_result or {}).get("cache_hit_rate_pct"),
        "scale_success_rate_pct": (scale_result or {}).get("success_rate_pct"),
    }

    freshness = (dq_result or {}).get("freshness") or {}

    health = "ok"
    if failures["gold_mismatches_n"]:
        health = "degraded"
    if (scale_result or {}).get("success_rate_pct") is not None and (scale_result or {}).get("success_rate_pct") < 80:
        health = "degraded"
    if any(not p.get("ok") for p in pipeline):
        health = "degraded"

    return {
        "as_of": now_iso(),
        "health": health,
        "pipeline": pipeline,
        "queues": queues,
        "failures": failures,
        "processing_time": processing,
        "cache": cache,
        "data_freshness": freshness,
        "gold_regression": {
            "status": (gold_result or {}).get("status"),
            "passed": (gold_result or {}).get("passed"),
            "mismatches_n": failures["gold_mismatches_n"],
        },
        "recommendation_policy": "hardening_diagnostics_only_no_buy_sell",
    }


def _pipe(name: str, h: dict[str, Any]) -> dict[str, Any]:
    status = h.get("status")
    ok = bool(h.get("_ok")) and not h.get("error") and status not in {"error", "disabled", "fail"}
    return {
        "component": name,
        "ok": ok,
        "status": status or ("ok" if ok else "error"),
        "version": h.get("version"),
        "error": h.get("error"),
    }


def _health_oie() -> dict[str, Any]:
    from opportunity_intelligence.production import health

    return health()


def _health_kde() -> dict[str, Any]:
    from knowledge_delta_engine.production import health

    return health()


def _health_iol() -> dict[str, Any]:
    from investment_operations.production import health

    return health()


def _health_aro() -> dict[str, Any]:
    from autonomous_research.production import health

    return health()


def _health_obs() -> dict[str, Any]:
    from observability.production import status

    return status()


def _health_mc() -> dict[str, Any]:
    from mission_control.production import health

    return health()

