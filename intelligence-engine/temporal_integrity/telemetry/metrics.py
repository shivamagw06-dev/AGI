"""TIRC telemetry snapshot."""

from __future__ import annotations

from typing import Any

from temporal_integrity import store as tirc_store
from temporal_integrity.schema import TIRC_VERSION


def snapshot() -> dict[str, Any]:
    reports = tirc_store.latest_reports(limit=100)
    rejected = tirc_store.latest_rejected(limit=100)
    cert = tirc_store.latest_certification()
    return {
        "tirc_version": TIRC_VERSION,
        "n_guard_reports": len(reports),
        "n_rejected_buffered": len(rejected),
        "objects_checked": sum(int(r.get("objects_checked") or 0) for r in reports),
        "objects_rejected": sum(int(r.get("objects_rejected") or 0) for r in reports),
        "certification": cert,
        "fabricated": False,
    }
