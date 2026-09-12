"""Mission Control / API dashboard for Temporal Integrity."""

from __future__ import annotations

from typing import Any

from temporal_integrity import store as tirc_store
from temporal_integrity.schema import COMPANY, MODULE_CODE, PROGRAMME, TIRC_VERSION


def build_board() -> dict[str, Any]:
    reports = tirc_store.latest_reports(limit=20)
    rejected = tirc_store.latest_rejected(limit=20)
    cert = tirc_store.latest_certification() or {}
    n_rej = sum(int(r.get("objects_rejected") or 0) for r in reports)
    n_chk = sum(int(r.get("objects_checked") or 0) for r in reports)
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "version": TIRC_VERSION,
        "replay_health": "healthy"
        if (cert.get("passed") is True)
        else ("degraded" if reports else "awaiting_runs"),
        "certification_status": cert.get("certification_result") or "PENDING",
        "future_leakage_count": cert.get("future_leakage_count"),
        "replay_accuracy_pct": cert.get("replay_accuracy_pct"),
        "objects_checked": n_chk,
        "objects_rejected": n_rej,
        "rejected_sample": [
            {
                "object_id": (r.get("contract") or {}).get("object_id"),
                "reason": (r.get("contract") or {}).get("reason_if_rejected"),
            }
            for r in rejected[:10]
        ],
        "latest_guard_reports": reports[:5],
        "institutional_guarantee": (
            "Historical replay answers use only information available at as_of"
        ),
        "fabricated": False,
    }
