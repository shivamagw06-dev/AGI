"""Production Hardening — façade for scale, observability, regression, DQ, performance."""

from __future__ import annotations

from typing import Any

from production_hardening.data_quality import run_data_quality
from production_hardening.observability import build_observability_board
from production_hardening.performance import run_performance_profile
from production_hardening.regression import run_gold_regression
from production_hardening.scale import run_scale_test
from production_hardening.schema import (
    ENGINE_CODE,
    ENGINE_NAME,
    GOLD_REGRESSION_UNIVERSE,
    MILESTONE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SCALE_PRESETS,
    VERSION,
    WORKSTREAM_ID,
)
from production_hardening import store as hstore
from production_hardening.util import now_iso
from production_hardening.universe import resolve_universe


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "role": "production_hardening",
        "not_an_intelligence_engine": True,
        "capabilities": [
            "scale_testing",
            "observability",
            "gold_regression",
            "data_quality",
            "performance_profiling",
        ],
        "gold_universe": list(GOLD_REGRESSION_UNIVERSE),
        "scale_presets": {k: v for k, v in SCALE_PRESETS.items()},
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def scale(
    *,
    preset: str = "smoke",
    limit: int | None = None,
    mode: str = "opportunity",
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    result = run_scale_test(preset=preset, limit=limit, mode=mode, symbols=symbols)
    hstore.append_history(
        {
            "kind": "scale",
            "preset": preset,
            "n": result.get("n"),
            "ok_n": result.get("ok_n"),
            "throughput_per_min": result.get("throughput_per_min"),
        }
    )
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **result}


def regression(*, update_baseline: bool = False, **kwargs: Any) -> dict[str, Any]:
    result = run_gold_regression(update_baseline=update_baseline, **kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **result}


def data_quality(**kwargs: Any) -> dict[str, Any]:
    result = run_data_quality(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **result}


def performance(**kwargs: Any) -> dict[str, Any]:
    result = run_performance_profile(**kwargs)
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **result}


def observability(
    *,
    include_gold: bool = True,
    include_perf: bool = True,
    include_dq: bool = True,
    scale_preset: str | None = None,
) -> dict[str, Any]:
    gold = run_gold_regression() if include_gold else None
    dq = run_data_quality() if include_dq else None
    perf = run_performance_profile() if include_perf else None
    scale_result = None
    if scale_preset:
        scale_result = run_scale_test(preset=scale_preset, mode="opportunity")
    board = build_observability_board(
        gold_result=gold,
        scale_result=scale_result,
        dq_result=dq,
        perf_result=perf,
    )
    return {"enabled": True, "engine": ENGINE_CODE, "version": VERSION, **board}


def dashboard() -> dict[str, Any]:
    """Hardening dashboard — gold + DQ + perf + pipeline health (no large scale by default)."""
    return observability(include_gold=True, include_perf=True, include_dq=True, scale_preset=None)


def universe_info(preset: str = "smoke", limit: int | None = None) -> dict[str, Any]:
    uni = resolve_universe(preset=preset, limit=limit)
    # Don't return full symbol list for large presets in API by default
    symbols = uni.get("symbols") or []
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "source": uni.get("source"),
        "n": uni.get("n"),
        "preset": uni.get("preset") or preset,
        "file": uni.get("file"),
        "sample": symbols[:20],
        "gold_universe": list(GOLD_REGRESSION_UNIVERSE),
    }


def history(limit: int = 20) -> dict[str, Any]:
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "runs": hstore.latest_history(limit=limit),
    }


def run_hardening_suite(
    *,
    update_baseline: bool = False,
    scale_preset: str = "smoke",
) -> dict[str, Any]:
    """Full hardening pass suitable for CI / overnight kickoff (smoke scale by default)."""
    gold = run_gold_regression(update_baseline=update_baseline)
    dq = run_data_quality()
    perf = run_performance_profile()
    scale_result = run_scale_test(preset=scale_preset, mode="opportunity")
    board = build_observability_board(
        gold_result=gold,
        scale_result=scale_result,
        dq_result=dq,
        perf_result=perf,
    )
    out = {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "as_of": now_iso(),
        "gold_regression": {
            "status": gold.get("status"),
            "passed": gold.get("passed"),
            "mismatches_n": len(gold.get("mismatches") or []),
            "ok_n": gold.get("ok_n"),
        },
        "data_quality": {
            "sla_pass_n": dq.get("sla_pass_n"),
            "n": dq.get("n"),
            "cache_hit_rate_pct": dq.get("cache_hit_rate_pct"),
            "failures_n": len(dq.get("failures") or []),
        },
        "performance": perf.get("avg_ms"),
        "scale": {
            "preset": scale_preset,
            "n": scale_result.get("n"),
            "ok_n": scale_result.get("ok_n"),
            "throughput_per_min": scale_result.get("throughput_per_min"),
            "latency_ms": scale_result.get("latency_ms"),
            "memory": scale_result.get("memory"),
        },
        "observability_health": board.get("health"),
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
    }
    hstore.append_history({"kind": "hardening_suite", "observability_health": board.get("health"), "scale_preset": scale_preset})
    return out
