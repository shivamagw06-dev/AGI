"""PRP-01 Performance Center diagnostics soft-slice."""

from __future__ import annotations

from typing import Any

from institutional_performance import cache as cache_mod
from institutional_performance.flags import flags_dict, max_workers
from institutional_performance.job_queue import get_queue
from institutional_performance.metrics import latency_snapshot, slow_queries
from institutional_performance.parallel import parallel_status
from institutional_performance.schema import (
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    PERF_ENGINE_VERSION,
    PRP_PRODUCT,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
    TARGET_ASK_CACHED_MS,
    TARGET_CONCURRENT_USERS,
    TARGET_WORKSPACE_MS,
)
from institutional_performance.streaming import streaming_capabilities


def performance_center_board() -> dict[str, Any]:
    cstats = cache_mod.stats()
    qstats = get_queue().stats()
    lat = latency_snapshot()
    return {
        "performance_center": True,
        "cache_hit_rate": cstats.get("hit_rate"),
        "cache_hits": cstats.get("hits"),
        "cache_misses": cstats.get("misses"),
        "redis_enabled": cstats.get("redis_enabled"),
        "p95_latency_seconds": lat.get("overall_p95_seconds"),
        "latency_by_operation": lat.get("by_operation"),
        "slow_queries": slow_queries(12),
        "queue_depth": qstats.get("queue_depth"),
        "active_workers": qstats.get("active_workers"),
        "jobs_completed": qstats.get("completed"),
        "jobs_failed": qstats.get("failed"),
        "max_workers": qstats.get("max_workers") or max_workers(),
        "parallel": parallel_status(),
        "streaming": streaming_capabilities(),
        "targets": {
            "ask_cached_ms": TARGET_ASK_CACHED_MS,
            "workspace_ms": TARGET_WORKSPACE_MS,
            "concurrent_users": TARGET_CONCURRENT_USERS,
        },
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "adds_intelligence_engines": False,
    }


def build_diagnostics() -> dict[str, Any]:
    return {
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "perf_engine_version": PERF_ENGINE_VERSION,
        "flags": flags_dict(),
        **performance_center_board(),
    }
