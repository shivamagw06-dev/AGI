"""Agent Map durable snapshot — HTTP reads only; worker builds.

Persists under $KIP_DATA_DIR/mission_control/agent_map.json
(same root / atomic helpers as Mission Control desk snapshot).
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from copy import deepcopy
from typing import Any, Optional

from mission_control.snapshot import _now, _read_json, _write_json, store_root

_LOCK = threading.RLock()
_WARM: dict[str, Any] | None = None
_META: dict[str, Any] = {
    "last_successful_at": None,
    "last_failure_at": None,
    "last_error": None,
    "last_trigger": None,
}
_JOB: dict[str, Any] = {
    "job_id": None,
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "trigger": None,
    "error": None,
}
_JOB_LOCK = threading.RLock()


def agent_map_path():
    return store_root() / "agent_map.json"


def put_agent_map(payload: dict[str, Any], *, trigger: str = "manual") -> dict[str, Any]:
    global _WARM
    body = deepcopy(payload) if isinstance(payload, dict) else {}
    meta = {
        "persisted_at": _now(),
        "trigger": trigger,
        "path": str(agent_map_path()),
        "durable": bool((os.getenv("KIP_DATA_DIR") or "").strip()),
        "source": "precomputed",
        "delivery": "snapshot",
    }
    snap_meta = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else {}
    body["snapshot"] = {**snap_meta, **meta}
    body["delivery"] = {"mode": "snapshot", "class": "agent_map"}
    body["status"] = "ready"
    _write_json(agent_map_path(), body)
    with _LOCK:
        _WARM = deepcopy(body)
        _META["last_successful_at"] = meta["persisted_at"]
        _META["last_trigger"] = trigger
        _META["last_error"] = None
    return meta


def get_agent_map() -> Optional[dict[str, Any]]:
    global _WARM
    with _LOCK:
        if isinstance(_WARM, dict) and (
            _WARM.get("agents") is not None or _WARM.get("summary") is not None
        ):
            return deepcopy(_WARM)
    disk = _read_json(agent_map_path())
    if isinstance(disk, dict) and (disk.get("agents") is not None or disk.get("summary") is not None):
        with _LOCK:
            _WARM = deepcopy(disk)
        return deepcopy(disk)
    return None


def job_status() -> dict[str, Any]:
    with _JOB_LOCK:
        return deepcopy(_JOB)


def _set_job(**kwargs: Any) -> None:
    with _JOB_LOCK:
        _JOB.update(kwargs)


def agent_map_meta() -> dict[str, Any]:
    snap = get_agent_map()
    with _LOCK:
        meta = deepcopy(_META)
    job = job_status()
    if not snap:
        return {
            "exists": False,
            "status": "warming" if job.get("status") in {"queued", "running"} else "missing",
            "job": job,
            **meta,
        }
    s = snap.get("snapshot") if isinstance(snap.get("snapshot"), dict) else {}
    return {
        "exists": True,
        "status": "ready",
        "persisted_at": s.get("persisted_at") or snap.get("generated_at"),
        "generated_at": snap.get("generated_at"),
        "trigger": s.get("trigger") or meta.get("last_trigger"),
        "durable": s.get("durable"),
        "path": s.get("path") or str(agent_map_path()),
        "job": job,
        **meta,
    }


def warming_payload(*, message: str | None = None) -> dict[str, Any]:
    from mission_control.agent_map import AGENT_MAP_VERSION

    meta = agent_map_meta()
    return {
        "status": "warming",
        "snapshot": None,
        "message": message or "Agent Map is initializing.",
        "enabled": True,
        "read_only": True,
        "programme": "AGIB Agent Map",
        "version": AGENT_MAP_VERSION,
        "delivery": {"mode": "snapshot", "class": "warming"},
        "snapshot_meta": meta,
        "summary": {
            "total": 0,
            "working": 0,
            "soft": 0,
            "off": 0,
            "orphan": 0,
            "degraded": 0,
            "unknown": 0,
            "working_or_soft": 0,
            "headline": "Agent Map warming — snapshot not ready yet",
        },
        "agents": [],
        "groups": [],
        "generated_at": None,
        "_warming": True,
    }


def read_agent_map() -> dict[str, Any]:
    """HTTP-safe: return snapshot or warming. Never calls build_agent_map()."""
    snap = get_agent_map()
    if snap:
        out = deepcopy(snap)
        out.setdefault("status", "ready")
        out["snapshot_meta"] = agent_map_meta()
        return out
    return warming_payload()


def build_and_persist_agent_map(*, trigger: str = "manual") -> dict[str, Any]:
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("MC_ALLOW_LIVE_IN_PYTEST") != "1":
        from mission_control.agent_map import AGENT_MAP_VERSION, GROUP_LABELS

        existing = get_agent_map() or {
            "enabled": True,
            "read_only": True,
            "programme": "AGIB Agent Map",
            "version": AGENT_MAP_VERSION,
            "generated_at": _now(),
            "summary": {
                "total": 3,
                "working": 2,
                "soft": 1,
                "off": 0,
                "orphan": 0,
                "degraded": 0,
                "unknown": 0,
                "working_or_soft": 3,
                "headline": "2 working · 1 soft-wire · 0 off · 0 orphan",
            },
            "production_flags": {},
            "status_legend": {},
            "groups": [
                {
                    "id": "cio",
                    "label": GROUP_LABELS.get("cio", "CIO"),
                    "agents": [],
                    "counts": {"working": 1, "soft": 0, "off": 0, "orphan": 0, "degraded": 0, "unknown": 0},
                }
            ],
            "agents": [
                {
                    "id": "cio",
                    "name": "CIO",
                    "group": "cio",
                    "group_label": GROUP_LABELS.get("cio", "CIO"),
                    "responsibility": "pytest stub",
                    "sources": [],
                    "status": "working",
                    "working": True,
                    "detail": "stub",
                    "probe": {},
                },
                {
                    "id": "faa",
                    "name": "FAA",
                    "group": "faa",
                    "group_label": GROUP_LABELS.get("faa", "FAA"),
                    "responsibility": "pytest stub",
                    "sources": [],
                    "status": "working",
                    "working": True,
                    "detail": "stub",
                    "probe": {},
                },
                {
                    "id": "macro_economist",
                    "name": "Macro",
                    "group": "research",
                    "group_label": GROUP_LABELS.get("research", "Research"),
                    "responsibility": "pytest stub",
                    "sources": [],
                    "status": "soft",
                    "working": False,
                    "detail": "stub",
                    "probe": {},
                },
            ],
        }
        meta = put_agent_map(existing, trigger=f"pytest:{trigger}")
        return {"ok": True, "trigger": trigger, "meta": meta, "pytest_stub": True}

    from mission_control.agent_map import build_agent_map

    body = build_agent_map()
    meta = put_agent_map(body, trigger=trigger)
    return {
        "ok": True,
        "trigger": trigger,
        "meta": meta,
        "generated_at": body.get("generated_at"),
        "summary": body.get("summary"),
    }


def enqueue_rebuild(*, trigger: str = "admin_rebuild", wait: bool = False) -> dict[str, Any]:
    with _JOB_LOCK:
        if _JOB.get("status") in {"queued", "running"}:
            already = True
            job_id = _JOB.get("job_id")
        else:
            already = False
            job_id = f"am-snap-{uuid.uuid4().hex[:12]}"
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
            "snapshot": agent_map_meta(),
            "message": "Agent Map rebuild already in progress; serving existing snapshot",
        }

    def _worker() -> None:
        _set_job(status="running")
        try:
            build_and_persist_agent_map(trigger=trigger)
            _set_job(status="completed", finished_at=_now(), error=None)
        except Exception as exc:  # noqa: BLE001
            with _LOCK:
                _META["last_failure_at"] = _now()
                _META["last_error"] = str(exc)[:240]
            _set_job(status="failed", finished_at=_now(), error=str(exc)[:240])

    if wait:
        _worker()
        return {
            "ok": True,
            "status": job_status().get("status"),
            "job_id": job_id,
            "snapshot": agent_map_meta(),
            "agent_map": get_agent_map() or warming_payload(),
        }

    threading.Thread(target=_worker, name=f"am-snap-{job_id}", daemon=True).start()
    return {
        "ok": True,
        "status": "queued",
        "job_id": job_id,
        "snapshot": agent_map_meta(),
        "message": "Agent Map snapshot rebuild queued; existing snapshot continues to serve",
    }


def reset_for_tests() -> None:
    global _WARM
    for _ in range(50):
        with _JOB_LOCK:
            status = _JOB.get("status")
        if status not in {"queued", "running"}:
            break
        time.sleep(0.02)
    with _LOCK:
        _WARM = None
        _META.update(
            {
                "last_successful_at": None,
                "last_failure_at": None,
                "last_error": None,
                "last_trigger": None,
            }
        )
        path = agent_map_path()
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
    with _LOCK:
        _WARM = None
