"""Latency, slow-query, and Mission Control performance metrics (PRP-01)."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from institutional_performance.schema import LATENCY_TARGET_SECONDS, PRP_01_ID

_lock = threading.Lock()
_samples: Deque[Dict[str, Any]] = deque(maxlen=2000)
_slow: Deque[Dict[str, Any]] = deque(maxlen=200)


def record_latency(
    operation: str,
    seconds: float,
    *,
    cached: bool = False,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    row = {
        "operation": operation,
        "seconds": round(float(seconds), 4),
        "cached": bool(cached),
        "ts": time.time(),
        "meta": dict(meta or {}),
    }
    with _lock:
        _samples.append(row)
        target = LATENCY_TARGET_SECONDS.get(operation)
        if target is not None and seconds > target and not cached:
            _slow.append(row)
        elif seconds > 2.0 and not cached:
            _slow.append(row)


def timed(operation: str, *, cached: bool = False):
    """Context manager / decorator helper."""

    class _Timer:
        def __enter__(self):
            self.t0 = time.perf_counter()
            return self

        def __exit__(self, *args):
            record_latency(operation, time.perf_counter() - self.t0, cached=cached)

    return _Timer()


def p95(operation: Optional[str] = None) -> Optional[float]:
    with _lock:
        vals = [
            s["seconds"]
            for s in _samples
            if operation is None or s["operation"] == operation
        ]
    if not vals:
        return None
    vals = sorted(vals)
    idx = max(0, int(0.95 * (len(vals) - 1)))
    return round(vals[idx], 4)


def mean(operation: Optional[str] = None) -> Optional[float]:
    with _lock:
        vals = [
            s["seconds"]
            for s in _samples
            if operation is None or s["operation"] == operation
        ]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def slow_queries(limit: int = 20) -> List[Dict[str, Any]]:
    with _lock:
        rows = list(_slow)[-limit:]
    return list(reversed(rows))


def latency_snapshot() -> Dict[str, Any]:
    ops = set(LATENCY_TARGET_SECONDS) | {
        s["operation"] for s in list(_samples)
    }
    by_op = {}
    for op in sorted(ops):
        by_op[op] = {
            "p95_seconds": p95(op),
            "mean_seconds": mean(op),
            "target_seconds": LATENCY_TARGET_SECONDS.get(op),
            "meets_target": (
                p95(op) is not None
                and LATENCY_TARGET_SECONDS.get(op) is not None
                and p95(op) <= LATENCY_TARGET_SECONDS[op]
            )
            if p95(op) is not None and LATENCY_TARGET_SECONDS.get(op)
            else None,
        }
    return {
        "id": PRP_01_ID,
        "sample_count": len(_samples),
        "by_operation": by_op,
        "overall_p95_seconds": p95(),
        "slow_query_count": len(_slow),
    }


def reset_metrics_for_tests() -> None:
    with _lock:
        _samples.clear()
        _slow.clear()
