"""Production observability — soft counters for institutional stack health."""

from __future__ import annotations

import threading
import time
from typing import Any

OBS_VERSION = "production-observability-v1.0.0"

_LOCK = threading.Lock()
_STARTED = time.time()
_COUNTERS: dict[str, int] = {
    "govern_answer_total": 0,
    "govern_answer_withheld": 0,
    "govern_answer_narrative": 0,
    "evidence_packs_built": 0,
    "portfolio_decisions": 0,
    "portfolio_withheld": 0,
    "derived_fundamentals_hits": 0,
    "derived_risk_hits": 0,
    "cal_proposals": 0,
    "cal_approvals": 0,
    "outcome_reviews": 0,
    "contract_incomplete": 0,
    "adversarial_failures": 0,
}
_LATENCIES_MS: list[float] = []


def record(event: str, *, latency_ms: float | None = None, **tags: Any) -> None:
    with _LOCK:
        if event in _COUNTERS:
            _COUNTERS[event] += 1
        else:
            _COUNTERS[event] = _COUNTERS.get(event, 0) + 1
        if latency_ms is not None:
            _LATENCIES_MS.append(float(latency_ms))
            if len(_LATENCIES_MS) > 500:
                del _LATENCIES_MS[:250]


def snapshot() -> dict[str, Any]:
    with _LOCK:
        lats = list(_LATENCIES_MS)
        counters = dict(_COUNTERS)
    p50 = p95 = None
    if lats:
        s = sorted(lats)
        p50 = round(s[len(s) // 2], 2)
        p95 = round(s[min(len(s) - 1, int(len(s) * 0.95))], 2)
    return {
        "obs_version": OBS_VERSION,
        "uptime_s": round(time.time() - _STARTED, 1),
        "counters": counters,
        "latency_ms": {"p50": p50, "p95": p95, "n": len(lats)},
    }


def reset() -> None:
    with _LOCK:
        for k in list(_COUNTERS):
            _COUNTERS[k] = 0
        _LATENCIES_MS.clear()


def health() -> dict[str, Any]:
    snap = snapshot()
    return {"status": "ok", **snap}
