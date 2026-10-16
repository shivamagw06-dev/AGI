"""Parallel orchestration helpers for independent intelligence fetches (PRP-01)."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from institutional_performance.flags import max_workers, parallel_orchestration_enabled
from institutional_performance.metrics import record_latency
from institutional_performance.schema import PRP_01_ID

logger = logging.getLogger(__name__)

FetchFn = Callable[[], Any]


def run_parallel(
    tasks: Dict[str, FetchFn],
    *,
    max_workers_override: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run independent named tasks in parallel when the flag is on.
    On failure of one task, others still complete; failed keys get {"error": ...}.
    """
    import time

    t0 = time.perf_counter()
    if not tasks:
        return {}
    if not parallel_orchestration_enabled() or len(tasks) == 1:
        out: Dict[str, Any] = {}
        for name, fn in tasks.items():
            try:
                out[name] = fn()
            except Exception as exc:  # noqa: BLE001
                logger.warning("PRP-01 serial task %s failed: %s", name, exc)
                out[name] = {"error": str(exc)}
        record_latency("parallel_orch", time.perf_counter() - t0)
        return out

    workers = min(int(max_workers_override or max_workers()), len(tasks))
    out = {}
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="prp01-orch") as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                out[name] = fut.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("PRP-01 parallel task %s failed: %s", name, exc)
                out[name] = {"error": str(exc)}
    record_latency("parallel_orch", time.perf_counter() - t0)
    return out


def gather_named(pairs: List[Tuple[str, FetchFn]]) -> Dict[str, Any]:
    return run_parallel({name: fn for name, fn in pairs})


def parallel_status() -> Dict[str, Any]:
    return {
        "id": PRP_01_ID,
        "enabled": parallel_orchestration_enabled(),
        "max_workers": max_workers(),
    }
