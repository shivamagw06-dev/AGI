"""PRP-01 production façades — cache / queue / metrics / Performance Center."""

from __future__ import annotations

import time
from typing import Any, Optional

from institutional_performance import cache as cache_mod
from institutional_performance.diagnostics import build_diagnostics, performance_center_board
from institutional_performance.flags import (
    async_publications_enabled,
    flags_dict,
    is_enabled,
    query_cache_enabled,
    workspace_cache_enabled,
)
from institutional_performance.graph_incremental import apply_incremental_update
from institutional_performance.job_queue import (
    enqueue_publication,
    get_queue,
    job_status,
    reset_queue_for_tests,
)
from institutional_performance.metrics import (
    latency_snapshot,
    record_latency,
    reset_metrics_for_tests,
    slow_queries,
)
from institutional_performance.parallel import run_parallel
from institutional_performance.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    PERF_ENGINE_VERSION,
    PRP_PRODUCT,
    PRP_ROLE,
    PRP_SPEC,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
    TARGET_ASK_CACHED_MS,
    TARGET_CONCURRENT_USERS,
    TARGET_WORKSPACE_MS,
)
from institutional_performance.streaming import streaming_capabilities

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    cache_mod.reset_for_tests()
    reset_metrics_for_tests()
    reset_queue_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "role": PRP_ROLE,
        "llm": False,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "perf_engine_version": PERF_ENGINE_VERSION,
        "targets": {
            "ask_cached_ms": TARGET_ASK_CACHED_MS,
            "workspace_ms": TARGET_WORKSPACE_MS,
            "concurrent_users": TARGET_CONCURRENT_USERS,
        },
        "cache": cache_mod.stats(),
        "queue": get_queue().stats() if is_enabled() else {},
        "streaming": streaming_capabilities(),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PRP_SPEC,
        "brand": "AGI",
        "programme": "PRP",
        "phase": "production_readiness",
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    board = performance_center_board()
    return {
        "status": h.get("status"),
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "llm": False,
        "performance_center": True,
        "adds_intelligence_engines": False,
        "architecture_frozen": True,
        **board,
    }


def cache_stats() -> dict[str, Any]:
    return {"ok": True, "workstream_id": PRP_WORKSTREAM_ID, **cache_mod.stats()}


def cache_get_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    ns = str(body.get("namespace") or "object")
    parts = body.get("parts") or body.get("key")
    if isinstance(parts, str):
        parts = [parts]
    parts = list(parts or [])
    val = cache_mod.get(ns, *parts) if parts else None
    return {
        "ok": True,
        "hit": val is not None,
        "namespace": ns,
        "value": val,
        "workstream_id": PRP_WORKSTREAM_ID,
    }


def cache_set_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    ns = str(body.get("namespace") or "object")
    parts = body.get("parts") or body.get("key")
    if isinstance(parts, str):
        parts = [parts]
    parts = list(parts or ["default"])
    key = cache_mod.set(ns, *parts, value=body.get("value"), ttl=body.get("ttl"))
    return {"ok": True, "key": key, "workstream_id": PRP_WORKSTREAM_ID}


def queue_stats_api() -> dict[str, Any]:
    return {"ok": True, "workstream_id": PRP_WORKSTREAM_ID, **get_queue().stats()}


def enqueue_job(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": PRP_WORKSTREAM_ID}
    body = dict(payload or {})
    kind = str(body.get("kind") or "cache_warmup")
    job = get_queue().enqueue(kind, body.get("payload") or body)
    return {"ok": True, "workstream_id": PRP_WORKSTREAM_ID, "job": job.to_dict(), "async": True}


def get_job(job_id: str) -> dict[str, Any]:
    row = job_status(job_id)
    if not row:
        return {"ok": False, "error": "job_not_found", "job_id": job_id}
    return {"ok": True, "workstream_id": PRP_WORKSTREAM_ID, "job": row}


def list_jobs_api(limit: int = 40) -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "jobs": get_queue().list_jobs(limit=limit),
    }


def metrics_api() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "latency": latency_snapshot(),
        "slow_queries": slow_queries(20),
        "cache": cache_mod.stats(),
        "queue": get_queue().stats(),
    }


def graph_incremental_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    if body.get("async"):
        job = get_queue().enqueue("graph_incremental", body)
        return {"ok": True, "async": True, "job": job.to_dict()}
    return {"ok": True, "async": False, **apply_incremental_update(body)}


def parallel_demo(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    names = list(body.get("tasks") or ["evidence", "decision", "risk"])
    t0 = time.perf_counter()

    def _mk(name: str):
        def _fn():
            time.sleep(float(body.get("sleep") or 0.01))
            return {"name": name, "ok": True}

        return _fn

    out = run_parallel({n: _mk(n) for n in names})
    return {
        "ok": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "results": out,
        "elapsed_seconds": round(time.perf_counter() - t0, 4),
    }


# --- Soft integration helpers (called from UAG / RW / PUB) ---


def maybe_get_query_cache(*parts: Any) -> Any | None:
    if not is_enabled() or not query_cache_enabled():
        return None
    return cache_mod.get("query", *parts)


def maybe_set_query_cache(*parts: Any, value: Any, ttl: Optional[int] = None) -> None:
    if not is_enabled() or not query_cache_enabled():
        return
    cache_mod.set("query", *parts, value=value, ttl=ttl)


def maybe_get_workspace_cache(*parts: Any) -> Any | None:
    if not is_enabled() or not workspace_cache_enabled():
        return None
    return cache_mod.get("workspace", *parts)


def maybe_set_workspace_cache(*parts: Any, value: Any, ttl: Optional[int] = None) -> None:
    if not is_enabled() or not workspace_cache_enabled():
        return
    cache_mod.set("workspace", *parts, value=value, ttl=ttl)


def maybe_enqueue_publication(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Return job envelope when async publication is requested and enabled."""
    if not is_enabled() or not async_publications_enabled():
        return None
    if payload.get("_prp_worker"):
        return None
    async_flag = payload.get("async")
    if async_flag is False:
        return None
    if async_flag is not True and not payload.get("background"):
        # Default: sync unless explicitly async/background
        return None
    job = enqueue_publication(payload)
    return {
        "ok": True,
        "async": True,
        "workstream_id": PRP_WORKSTREAM_ID,
        "job": job,
        "status": job.get("status"),
        "job_id": job.get("job_id"),
        "compose_only": True,
        "analyzes": False,
        "note": "Publication generation queued; poll GET /v1/performance/jobs/{job_id}.",
    }


def record_op_latency(operation: str, seconds: float, *, cached: bool = False) -> None:
    if is_enabled():
        record_latency(operation, seconds, cached=cached)
