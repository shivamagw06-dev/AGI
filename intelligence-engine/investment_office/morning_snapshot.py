"""IO V1.3.1 — durable Morning Snapshot (precomputed desk; hot path reads only).

Persists under $KIP_DATA_DIR/investment_office (CGL-style atomic JSON).
Heavy ICF/IEP/CGL work runs in the builder, never synchronously on page load.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_WARM: Dict[str, Any] | None = None
_JOB: Dict[str, Any] = {
    "job_id": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "trigger": None,
    "error": None,
}
_JOB_LOCK = threading.RLock()


def store_root() -> Path:
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    raw = (os.getenv("IO_MORNING_SNAPSHOT_ROOT") or "").strip()
    if raw:
        root = Path(raw)
    elif kip:
        root = Path(kip) / "investment_office"
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "investment_office"
    root.mkdir(parents=True, exist_ok=True)
    return root


def snapshot_path() -> Path:
    return store_root() / "morning_snapshot.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    try:
        from institutional_data.persistence.atomic import atomic_write_json, file_lock

        with file_lock(path):
            atomic_write_json(path, payload)
        return
    except Exception:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def put_snapshot(payload: dict[str, Any], *, trigger: str = "manual") -> dict[str, Any]:
    """Persist snapshot + warm in-process copy.

    Disk I/O happens outside the in-process lock so readers never deadlock
    against flock / slow writes.
    """
    global _WARM
    body = deepcopy(payload) if isinstance(payload, dict) else {}
    meta = {
        "persisted_at": _now(),
        "trigger": trigger,
        "path": str(snapshot_path()),
        "durable": bool((os.getenv("KIP_DATA_DIR") or "").strip()),
    }
    body["snapshot"] = {
        **(body.get("snapshot") if isinstance(body.get("snapshot"), dict) else {}),
        **meta,
        "source": "precomputed",
    }
    body["delivery"] = {
        "mode": "snapshot",
        "class": "morning_brief",
        "freshness": "daily_plus_manual_refresh",
    }
    # Write first (may take flock); then publish warm copy under the lock.
    _write_json(snapshot_path(), body)
    with _LOCK:
        _WARM = deepcopy(body)
    return meta


def get_snapshot() -> Optional[dict[str, Any]]:
    """Warm memory first, then disk. Never rebuilds."""
    global _WARM
    with _LOCK:
        if isinstance(_WARM, dict) and _WARM.get("ok"):
            return deepcopy(_WARM)
    # Disk read outside lock — avoid blocking writers / flock.
    disk = _read_json(snapshot_path())
    if isinstance(disk, dict) and disk.get("ok"):
        with _LOCK:
            _WARM = deepcopy(disk)
        return deepcopy(disk)
    return None


def snapshot_meta() -> dict[str, Any]:
    snap = get_snapshot()
    if not snap:
        return {"exists": False, "job": job_status()}
    s = snap.get("snapshot") if isinstance(snap.get("snapshot"), dict) else {}
    return {
        "exists": True,
        "persisted_at": s.get("persisted_at") or snap.get("generated_at"),
        "trigger": s.get("trigger"),
        "durable": s.get("durable"),
        "version": snap.get("version"),
        "generated_at": snap.get("generated_at"),
        "job": job_status(),
    }


def job_status() -> dict[str, Any]:
    with _JOB_LOCK:
        return deepcopy(_JOB)


def _set_job(**kwargs: Any) -> None:
    with _JOB_LOCK:
        _JOB.update(kwargs)


def build_and_persist_morning_snapshot(
    *,
    trigger: str = "manual",
    force: bool = True,
) -> dict[str, Any]:
    """Run expensive aggregate once and persist. Soft — callers should try/except."""
    # Unit tests must not pull ICF/IEP/CGL. Opt in with IO_ALLOW_LIVE_IN_PYTEST=1.
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("IO_ALLOW_LIVE_IN_PYTEST") != "1":
        existing = get_snapshot() or {
            "ok": True,
            "top_summary": {},
            "executive_brief": {"narrative": "pytest stub"},
            "generated_at": _now(),
            "building": False,
        }
        meta = put_snapshot(existing, trigger=f"pytest:{trigger}")
        return {
            "ok": True,
            "trigger": trigger,
            "meta": meta,
            "pytest_stub": True,
            "top_summary": existing.get("top_summary"),
            "generated_at": existing.get("generated_at") or _now(),
        }

    from investment_office.morning_desk import build_morning_overview

    overview = build_morning_overview(force=force, persist_snapshot=False)
    meta = put_snapshot(overview, trigger=trigger)
    return {
        "ok": True,
        "trigger": trigger,
        "meta": meta,
        "top_summary": overview.get("top_summary"),
        "generated_at": overview.get("generated_at"),
    }


def after_cgl_cycle(run: dict[str, Any] | None = None) -> dict[str, Any]:
    """Soft hook after CGL (+ KIL). Never raises to orchestrator."""
    try:
        slot = (run or {}).get("slot") or "cgl"
        return build_and_persist_morning_snapshot(trigger=f"cgl:{slot}", force=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200], "soft_wire": True, "trigger": "cgl"}


def after_scheduler_ready(result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Soft hook after morning DAG READY. Never raises to scheduler."""
    try:
        _ = result
        return build_and_persist_morning_snapshot(trigger="morning_dag_ready", force=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200], "soft_wire": True, "trigger": "morning_dag"}


def enqueue_refresh(*, trigger: str = "admin_refresh", wait: bool = False) -> dict[str, Any]:
    """Async snapshot rebuild. Returns immediately unless wait=True."""
    # Important: never call snapshot_meta()/job_status() while holding _JOB_LOCK
    # (_JOB_LOCK is a non-reentrant Lock; nested acquire deadlocks).
    with _JOB_LOCK:
        if _JOB.get("status") in {"queued", "running"}:
            existing_id = _JOB.get("job_id")
            already = True
            job_id = existing_id
        else:
            already = False
            job_id = f"io-snap-{uuid.uuid4().hex[:12]}"
            _JOB.update(
                {
                    "job_id": job_id,
                    "status": "queued",
                    "started_at": _now(),
                    "finished_at": None,
                    "trigger": trigger,
                    "error": None,
                }
            )

    if already:
        return {
            "ok": True,
            "status": "already_running",
            "job_id": job_id,
            "snapshot": snapshot_meta(),
            "message": "Rebuild already in progress; serving existing snapshot",
        }

    def _worker() -> None:
        _set_job(status="running")
        try:
            build_and_persist_morning_snapshot(trigger=trigger, force=True)
            _set_job(status="completed", finished_at=_now(), error=None)
        except Exception as exc:
            _set_job(status="failed", finished_at=_now(), error=str(exc)[:240])

    if wait:
        _worker()
        return {
            "ok": True,
            "status": job_status().get("status"),
            "job_id": job_id,
            "snapshot": snapshot_meta(),
            "overview": get_snapshot(),
        }

    threading.Thread(target=_worker, name=f"io-morning-snap-{job_id}", daemon=True).start()
    return {
        "ok": True,
        "status": "queued",
        "job_id": job_id,
        "snapshot": snapshot_meta(),
        "message": "Morning snapshot rebuild queued; existing snapshot continues to serve",
    }


def live_system_health() -> dict[str, Any]:
    """Seconds-fresh operational status — no ICF/IEP/CGL scans."""
    flags: Dict[str, Any] = {}
    try:
        from investment_office.flags import flags_dict, is_enabled

        flags = {"io": flags_dict(), "enabled": is_enabled()}
    except Exception:
        flags = {}
    cgl_status = None
    try:
        from continuous_gather_learn.flags import is_enabled as cgl_on

        cgl_status = "enabled" if cgl_on() else "disabled"
    except Exception:
        cgl_status = "unknown"
    return {
        "ok": True,
        "class": "live_status",
        "freshness": "seconds",
        "generated_at": _now(),
        "snapshot": snapshot_meta(),
        "job": job_status(),
        "flags": flags,
        "cgl": {"status": cgl_status},
        "route": "/admin/investment-office",
    }


def reset_for_tests() -> None:
    global _WARM
    with _LOCK:
        _WARM = None
        path = snapshot_path()
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
    _set_job(
        job_id=None,
        status="idle",
        started_at=None,
        finished_at=None,
        trigger=None,
        error=None,
    )
