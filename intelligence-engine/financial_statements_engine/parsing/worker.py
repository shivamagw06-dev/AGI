"""Parser worker helpers — isolation + checkpoints."""

from __future__ import annotations

from typing import Any, Callable

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def checkpoint(job_id: str, stage: str, payload: dict[str, Any] | None = None) -> None:
    root = ensure_dirs()
    path = root / "parsing" / "checkpoints" / f"{job_id}.json"
    write_json_atomic(
        path,
        {"job_id": job_id, "stage": stage, "payload": payload or {}, "ts": now_iso()},
    )


def run_isolated(fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Run parse callable; convert crashes to structured failure (process continues)."""
    try:
        return fn()
    except Exception as exc:  # pragma: no cover - defensive isolation
        return {
            "ok": False,
            "errors": ["parse_failure"],
            "error_detail": str(exc),
            "writes_warehouse": False,
        }
