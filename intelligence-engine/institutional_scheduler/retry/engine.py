"""Retry engine — count, backoff, partial retry, failure isolation, alerts."""

from __future__ import annotations

import time
from typing import Any, Callable

from institutional_scheduler import store
from institutional_scheduler.schema import DEFAULT_RETRY


def run_with_retry(
    fn: Callable[[], dict[str, Any]],
    *,
    workflow_id: str,
    retry_policy: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    policy = {**DEFAULT_RETRY, **(retry_policy or {})}
    max_attempts = int(policy.get("max_attempts") or 1)
    backoff = list(policy.get("backoff_seconds") or [1])
    attempts: list[dict[str, Any]] = []
    last: dict[str, Any] = {}

    if dry_run:
        return {
            "status": "ok",
            "dry_run": True,
            "workflow_id": workflow_id,
            "attempts": [{"n": 0, "status": "dry_run"}],
            "retries": 0,
            "payload": {"dry_run": True, "workflow_id": workflow_id},
            "fabricated": False,
        }

    for n in range(1, max_attempts + 1):
        t0 = time.time()
        try:
            last = fn() or {}
            status = last.get("status") or "ok"
            ok = status in {"ok", "skipped", "skipped_already_ready", "degraded", "partial"}
            attempts.append(
                {
                    "n": n,
                    "status": status if ok else "error",
                    "duration_ms": int((time.time() - t0) * 1000),
                    "error": None if ok else last.get("error"),
                }
            )
            if ok:
                return {
                    **last,
                    "status": status,
                    "workflow_id": workflow_id,
                    "attempts": attempts,
                    "retries": n - 1,
                    "permanent_failure": False,
                }
        except Exception as exc:
            last = {"status": "error", "error": str(exc)[:240], "fabricated": False}
            attempts.append(
                {
                    "n": n,
                    "status": "error",
                    "duration_ms": int((time.time() - t0) * 1000),
                    "error": str(exc)[:240],
                }
            )
        if n < max_attempts:
            delay = backoff[min(n - 1, len(backoff) - 1)]
            time.sleep(float(delay))

    store.alert("operator", f"Permanent failure: {workflow_id}", workflow_id=workflow_id)
    return {
        **last,
        "status": "error",
        "workflow_id": workflow_id,
        "attempts": attempts,
        "retries": max_attempts - 1,
        "permanent_failure": True,
        "failure_isolated": True,
        "operator_alert": True,
    }
