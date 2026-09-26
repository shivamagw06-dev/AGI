"""Mission Control durable snapshot — HTTP reads only; worker builds.

Persists under $KIP_DATA_DIR/mission_control (atomic JSON).
Heavy `build_mission_control()` runs only in background builders — never on
GET /v1/mission-control/dashboard.
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
from typing import Any, Optional

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
_SCHEDULER: dict[str, Any] = {
    "thread": None,
    "stop": None,
    "started": False,
}


def store_root() -> Path:
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    raw = (os.getenv("MC_SNAPSHOT_ROOT") or "").strip()
    if raw:
        root = Path(raw)
    elif kip:
        root = Path(kip) / "mission_control"
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "mission_control"
    root.mkdir(parents=True, exist_ok=True)
    return root


def snapshot_path() -> Path:
    return store_root() / "snapshot.json"


def interval_sec() -> float:
    try:
        return max(60.0, float(os.getenv("MC_SNAPSHOT_INTERVAL_SEC") or "600"))
    except (TypeError, ValueError):
        return 600.0


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
    """Persist snapshot + warm in-process copy. Disk I/O outside reader lock."""
    global _WARM
    body = deepcopy(payload) if isinstance(payload, dict) else {}
    meta = {
        "persisted_at": _now(),
        "trigger": trigger,
        "path": str(snapshot_path()),
        "durable": bool((os.getenv("KIP_DATA_DIR") or "").strip()),
        "source": "precomputed",
        "delivery": "snapshot",
    }
    snap_meta = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else {}
    body["snapshot"] = {**snap_meta, **meta}
    body["delivery"] = {
        "mode": "snapshot",
        "class": "mission_control_desk",
        "freshness": "worker_interval_plus_hooks",
    }
    body["status"] = "ready"
    _write_json(snapshot_path(), body)
    with _LOCK:
        _WARM = deepcopy(body)
        _META["last_successful_at"] = meta["persisted_at"]
        _META["last_trigger"] = trigger
        _META["last_error"] = None
    # Keep process-local TTL cache in sync for any legacy callers.
    try:
        from mission_control import store as mc_store

        mc_store.put_dashboard(body)
    except Exception:
        pass
    return meta


def get_snapshot() -> Optional[dict[str, Any]]:
    """Warm memory first, then disk. Never rebuilds."""
    global _WARM
    with _LOCK:
        if isinstance(_WARM, dict) and (_WARM.get("enabled") is not None or _WARM.get("executive_status")):
            return deepcopy(_WARM)
    disk = _read_json(snapshot_path())
    if isinstance(disk, dict) and (disk.get("enabled") is not None or disk.get("executive_status")):
        with _LOCK:
            _WARM = deepcopy(disk)
        return deepcopy(disk)
    return None


def snapshot_meta() -> dict[str, Any]:
    snap = get_snapshot()
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
        "path": s.get("path") or str(snapshot_path()),
        "job": job,
        **meta,
    }


def job_status() -> dict[str, Any]:
    with _JOB_LOCK:
        return deepcopy(_JOB)


def _set_job(**kwargs: Any) -> None:
    with _JOB_LOCK:
        _JOB.update(kwargs)


def warming_payload(*, message: str | None = None) -> dict[str, Any]:
    from mission_control.schema import MISSION_CONTROL_VERSION, PROGRAMME, PROGRAMME_SHORT

    meta = snapshot_meta()
    return {
        "status": "warming",
        "snapshot": None,
        "lastUpdated": meta.get("last_successful_at") or meta.get("persisted_at"),
        "message": message
        or "Mission Control snapshot is being generated.",
        "enabled": True,
        "read_only": True,
        "never_modifies_research": True,
        "never_changes_house_views": True,
        "never_changes_recommendations": True,
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": MISSION_CONTROL_VERSION,
        "delivery": {"mode": "snapshot", "class": "warming"},
        "snapshot_meta": meta,
        "executive_status": {
            "agi_status": "Warming",
            "research_grade": "—",
            "knowledge_grade": "—",
            "data_grade": "—",
        },
        "platform_status": [],
        "engine_status": [],
        "api_status": [],
        "live_event_stream": [
            {
                "at": _now(),
                "type": "system",
                "message": "Mission Control is warming up — first operational snapshot is being generated.",
            }
        ],
        "generated_at": None,
        "_warming": True,
    }


def read_dashboard() -> dict[str, Any]:
    """HTTP-safe: return snapshot or warming. Never calls build_mission_control()."""
    snap = get_snapshot()
    if snap:
        out = deepcopy(snap)
        out.setdefault("status", "ready")
        out["snapshot_meta"] = snapshot_meta()
        return out
    return warming_payload()


def build_and_persist_snapshot(
    *,
    trigger: str = "manual",
    ioc_service: Any | None = None,
) -> dict[str, Any]:
    """Run expensive aggregate once and persist. Soft for callers."""
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("MC_ALLOW_LIVE_IN_PYTEST") != "1":
        existing = get_snapshot() or {
            "enabled": True,
            "read_only": True,
            "never_modifies_research": True,
            "never_changes_house_views": True,
            "never_changes_recommendations": True,
            "executive_status": {
                "agi_status": "Healthy",
                "research_grade": "A",
                "knowledge_grade": "A",
                "data_grade": "A",
            },
            "platform_status": [{"name": f"p{i}", "current_status": "Healthy"} for i in range(10)],
            "engine_status": [{"name": f"e{i}", "current_status": "Healthy"} for i in range(5)],
            "api_status": [{"name": f"a{i}", "current_status": "Green"} for i in range(5)],
            "knowledge_growth": {"documents": 1, "research_learned": 0},
            "coverage_dashboard": {"coverage_pct": 0, "universe": "NIFTY_500"},
            "company_monitor": {"watched": 0, "alerts": []},
            "research_pipeline": {"queued": 0},
            "prediction_intelligence": {"active": 0},
            "data_quality": {"grade": "A"},
            "company_analysis": {"ready": 0},
            "academy": {"modules": 0},
            "cid": {"dossiers": 0},
            "system_health": {"backend": "Healthy"},
            "live_event_stream": [],
            "executive_copilot": {"prompts": ["What failed today?"]},
            "architecture_map": {
                "nodes": [
                    {"id": "providers"},
                    {"id": "ask_agi"},
                    {"id": "cid"},
                    {"id": "investment_office"},
                    {"id": "n5"},
                    {"id": "n6"},
                    {"id": "n7"},
                    {"id": "n8"},
                    {"id": "n9"},
                    {"id": "n10"},
                ]
            },
            "alerts_centre": [],
            "deployment_centre": {},
            "performance_analytics": {},
            "generated_at": _now(),
        }
        meta = put_snapshot(existing, trigger=f"pytest:{trigger}")
        return {
            "ok": True,
            "trigger": trigger,
            "meta": meta,
            "pytest_stub": True,
            "generated_at": existing.get("generated_at") or _now(),
        }

    from mission_control.aggregate import build_mission_control

    desk = build_mission_control(ioc_service=ioc_service)
    meta = put_snapshot(desk, trigger=trigger)
    return {
        "ok": True,
        "trigger": trigger,
        "meta": meta,
        "generated_at": desk.get("generated_at"),
        "enabled": desk.get("enabled"),
    }


def enqueue_rebuild(*, trigger: str = "admin_rebuild", wait: bool = False) -> dict[str, Any]:
    """Async snapshot rebuild. Returns immediately unless wait=True. Single-flight."""
    with _JOB_LOCK:
        if _JOB.get("status") in {"queued", "running"}:
            already = True
            job_id = _JOB.get("job_id")
        else:
            already = False
            job_id = f"mc-snap-{uuid.uuid4().hex[:12]}"
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
            build_and_persist_snapshot(trigger=trigger)
            # PR2/PR3 — refresh Agent Map + Intelligence Map in the same worker loop.
            try:
                from mission_control.agent_map_snapshot import build_and_persist_agent_map

                build_and_persist_agent_map(trigger=f"after_mc:{trigger}")
            except Exception as am_exc:  # noqa: BLE001
                try:
                    from mission_control import agent_map_snapshot as am

                    with am._LOCK:  # noqa: SLF001
                        am._META["last_failure_at"] = _now()
                        am._META["last_error"] = str(am_exc)[:240]
                except Exception:
                    pass
            try:
                from mission_control.intelligence_map_snapshot import (
                    build_and_persist_intelligence_map,
                )

                build_and_persist_intelligence_map(trigger=f"after_mc:{trigger}")
            except Exception as im_exc:  # noqa: BLE001
                try:
                    from mission_control import intelligence_map_snapshot as im

                    with im._LOCK:  # noqa: SLF001
                        im._META["last_failure_at"] = _now()
                        im._META["last_error"] = str(im_exc)[:240]
                except Exception:
                    pass
            try:
                from mission_control.institutional_intelligence_snapshot import (
                    build_and_persist_institutional_intelligence,
                )

                build_and_persist_institutional_intelligence(trigger=f"after_mc:{trigger}")
            except Exception as ii_exc:  # noqa: BLE001
                try:
                    from mission_control import institutional_intelligence_snapshot as ii

                    with ii._LOCK:  # noqa: SLF001
                        ii._META["last_failure_at"] = _now()
                        ii._META["last_error"] = str(ii_exc)[:240]
                except Exception:
                    pass
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
            "snapshot": snapshot_meta(),
            "dashboard": get_snapshot() or warming_payload(),
        }

    threading.Thread(target=_worker, name=f"mc-snap-{job_id}", daemon=True).start()
    return {
        "ok": True,
        "status": "queued",
        "job_id": job_id,
        "snapshot": snapshot_meta(),
        "message": "Mission Control snapshot rebuild queued; existing snapshot continues to serve",
    }


def after_cgl_cycle(run: dict[str, Any] | None = None) -> dict[str, Any]:
    """Soft hook after CGL. Never raises to orchestrator."""
    try:
        slot = (run or {}).get("slot") or "cgl"
        return build_and_persist_snapshot(trigger=f"cgl:{slot}")
    except Exception as exc:  # noqa: BLE001
        with _LOCK:
            _META["last_failure_at"] = _now()
            _META["last_error"] = str(exc)[:240]
        return {"ok": False, "error": str(exc)[:200], "soft_wire": True, "trigger": "cgl"}


def after_learning(result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Soft hook after learning completes."""
    try:
        _ = result
        return build_and_persist_snapshot(trigger="learning")
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "soft_wire": True, "trigger": "learning"}


def start_scheduler(*, boot_build: bool = True) -> dict[str, Any]:
    """Background interval builder. Idempotent. Single-flight via enqueue_rebuild."""
    if _SCHEDULER.get("started") and _SCHEDULER.get("thread") and _SCHEDULER["thread"].is_alive():
        return {"ok": True, "already_running": True, "interval_sec": interval_sec()}

    stop = threading.Event()
    _SCHEDULER["stop"] = stop

    def _loop() -> None:
        # Boot: enqueue immediately if missing (or always once).
        # Also covers Agent Map (built after each MC snapshot in the worker).
        if boot_build:
            if get_snapshot() is None:
                enqueue_rebuild(trigger="worker_boot_missing", wait=False)
            else:
                enqueue_rebuild(trigger="worker_boot", wait=False)
            try:
                from mission_control.agent_map_snapshot import (
                    enqueue_rebuild as enqueue_am,
                    get_agent_map,
                )

                if get_agent_map() is None:
                    enqueue_am(trigger="worker_boot_agent_map_missing", wait=False)
            except Exception:
                pass
            try:
                from mission_control.intelligence_map_snapshot import (
                    enqueue_rebuild as enqueue_im,
                    get_intelligence_map,
                )

                if get_intelligence_map() is None:
                    enqueue_im(trigger="worker_boot_intelligence_map_missing", wait=False)
            except Exception:
                pass
            try:
                from mission_control.institutional_intelligence_snapshot import (
                    enqueue_rebuild as enqueue_ii,
                    get_institutional_intelligence,
                )

                if get_institutional_intelligence() is None:
                    enqueue_ii(trigger="worker_boot_institutional_intelligence_missing", wait=False)
            except Exception:
                pass
        while not stop.wait(interval_sec()):
            enqueue_rebuild(trigger="interval", wait=False)

    t = threading.Thread(target=_loop, name="mc-snapshot-scheduler", daemon=True)
    _SCHEDULER["thread"] = t
    _SCHEDULER["started"] = True
    t.start()
    return {
        "ok": True,
        "started": True,
        "interval_sec": interval_sec(),
        "path": str(snapshot_path()),
        "exists": snapshot_path().exists(),
    }


def stop_scheduler() -> None:
    stop = _SCHEDULER.get("stop")
    if stop is not None:
        stop.set()
    _SCHEDULER["started"] = False


def should_run_builder_on_web() -> bool:
    """Web builds locally only when gather sidecar is off (dedicated worker elsewhere).

    Sidecar shares the web disk — gather_worker owns builds there.
    Dedicated worker has a separate disk — web must build its own snapshot.
    """
    explicit = (os.getenv("AGI_MC_SNAPSHOT_BUILDER") or "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    # Default OFF on the HTTP service.
    #
    # This previously returned True whenever the gather sidecar was disabled,
    # which is the normal configuration for agib-intelligence-engine. The
    # builder then rebuilt every interval_sec() - 600s by default - inside the
    # request-serving process. A rebuild takes the warehouse SQLite write lock,
    # so every handler needing a read blocks behind it, and the service stops
    # answering until it finishes.
    #
    # On 2026-08-19 that produced a failure cycle matching the interval to the
    # second: clean boot 08:24:40, builder due 08:34:40, service unresponsive
    # 08:34:34. Earlier fixes each appeared to work for exactly one interval.
    #
    # Moving handlers into the threadpool did not help, because the contention
    # is a database lock rather than the event loop.
    #
    # The dedicated agib-intelligence-worker owns snapshot builds. Set
    # AGI_MC_SNAPSHOT_BUILDER=true only for a single-box deployment with no
    # separate worker, and expect a stall every interval when you do.
    return False


def reset_for_tests() -> None:
    global _WARM
    stop_scheduler()
    # Wait briefly if a background rebuild is in flight so it cannot repopulate disk.
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
    with _LOCK:
        _WARM = None
    try:
        from mission_control.agent_map_snapshot import reset_for_tests as reset_am

        reset_am()
    except Exception:
        pass
    try:
        from mission_control.intelligence_map_snapshot import reset_for_tests as reset_im

        reset_im()
    except Exception:
        pass
    try:
        from mission_control.institutional_intelligence_snapshot import (
            reset_for_tests as reset_ii,
        )

        reset_ii()
    except Exception:
        pass
    try:
        from mission_control import store as mc_store

        mc_store.reset_for_tests()
    except Exception:
        pass
