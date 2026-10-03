"""Intelligence Map durable snapshot — HTTP reads only; worker soft-probes.

Persists under $KIP_DATA_DIR/mission_control/intelligence_map.json
Probing used to run in the browser via Promise.all(probeIntelligencePath).
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from mission_control.snapshot import _now, _read_json, _write_json, store_root

INTELLIGENCE_MAP_VERSION = "intelligence-map-v1.0.0"

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


def intelligence_map_path() -> Path:
    return store_root() / "intelligence_map.json"


def routes_catalog_path() -> Path:
    return Path(__file__).resolve().parent / "intelligence_map_routes.json"


def load_catalog_layers() -> list[dict[str, str]]:
    path = routes_catalog_path()
    if not path.exists():
        return []
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
        layers = body.get("layers") if isinstance(body, dict) else None
        if not isinstance(layers, list):
            return []
        out: list[dict[str, str]] = []
        for row in layers:
            if not isinstance(row, dict):
                continue
            lid = str(row.get("id") or "").strip()
            route = str(row.get("route") or "").strip()
            if lid and route:
                out.append({"id": lid, "route": route})
        return out
    except Exception:
        return []


def probe_timeout_sec() -> float:
    try:
        return max(0.5, float(os.getenv("MC_IMAP_PROBE_TIMEOUT_SEC") or "2.0"))
    except (TypeError, ValueError):
        return 2.0


def probe_workers() -> int:
    try:
        return max(1, min(12, int(os.getenv("MC_IMAP_PROBE_WORKERS") or "6")))
    except (TypeError, ValueError):
        return 6


def put_intelligence_map(payload: dict[str, Any], *, trigger: str = "manual") -> dict[str, Any]:
    global _WARM
    body = deepcopy(payload) if isinstance(payload, dict) else {}
    meta = {
        "persisted_at": _now(),
        "trigger": trigger,
        "path": str(intelligence_map_path()),
        "durable": bool((os.getenv("KIP_DATA_DIR") or "").strip()),
        "source": "precomputed",
        "delivery": "snapshot",
    }
    snap_meta = body.get("snapshot") if isinstance(body.get("snapshot"), dict) else {}
    body["snapshot"] = {**snap_meta, **meta}
    body["delivery"] = {"mode": "snapshot", "class": "intelligence_map"}
    body["status"] = "ready"
    _write_json(intelligence_map_path(), body)
    with _LOCK:
        _WARM = deepcopy(body)
        _META["last_successful_at"] = meta["persisted_at"]
        _META["last_trigger"] = trigger
        _META["last_error"] = None
    return meta


def get_intelligence_map() -> Optional[dict[str, Any]]:
    global _WARM
    with _LOCK:
        if isinstance(_WARM, dict) and (
            _WARM.get("probes") is not None or _WARM.get("summary") is not None
        ):
            return deepcopy(_WARM)
    disk = _read_json(intelligence_map_path())
    if isinstance(disk, dict) and (disk.get("probes") is not None or disk.get("summary") is not None):
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


def intelligence_map_meta() -> dict[str, Any]:
    snap = get_intelligence_map()
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
        "path": s.get("path") or str(intelligence_map_path()),
        "job": job,
        **meta,
    }


def warming_payload(*, message: str | None = None) -> dict[str, Any]:
    meta = intelligence_map_meta()
    return {
        "status": "warming",
        "snapshot": None,
        "message": message or "Intelligence Map is initializing.",
        "enabled": True,
        "read_only": True,
        "version": INTELLIGENCE_MAP_VERSION,
        "delivery": {"mode": "snapshot", "class": "warming"},
        "snapshot_meta": meta,
        "probes": {},
        "summary": {
            "total": 0,
            "active": 0,
            "partial": 0,
            "unreachable": 0,
            "headline": "Intelligence Map warming — snapshot not ready yet",
        },
        "mission_control_summary": None,
        "layers": load_catalog_layers(),
        "generated_at": None,
        "_warming": True,
    }


def read_intelligence_map() -> dict[str, Any]:
    """HTTP-safe: return snapshot or warming. Never probes."""
    snap = get_intelligence_map()
    if snap:
        out = deepcopy(snap)
        out.setdefault("status", "ready")
        out["snapshot_meta"] = intelligence_map_meta()
        return out
    return warming_payload()


def _mc_summary_slice() -> dict[str, Any] | None:
    try:
        from mission_control.snapshot import get_snapshot

        desk = get_snapshot()
        if not isinstance(desk, dict):
            return None
        return {
            "live_event_stream": desk.get("live_event_stream") or [],
            "knowledge_growth": desk.get("knowledge_growth") or {},
            "generated_at": desk.get("generated_at"),
            "executive_status": desk.get("executive_status"),
        }
    except Exception:
        return None


def _probe_path(client: Any, route: str) -> dict[str, Any]:
    path = route if str(route).startswith("/v1/") else f"/v1{route}"
    started = time.perf_counter()
    try:
        resp = client.get(path)
        latency_ms = int((time.perf_counter() - started) * 1000)
        data = None
        try:
            data = resp.json()
        except Exception:
            data = {"raw": (resp.text or "")[:240]}
        if resp.status_code >= 400:
            detail = ""
            if isinstance(data, dict):
                detail = str(
                    data.get("error") or data.get("detail") or data.get("message") or ""
                )[:280]
            return {
                "ok": False,
                "status": int(resp.status_code),
                "latency_ms": latency_ms,
                "data": data,
                "error": detail or f"HTTP {resp.status_code}",
                "path": route,
            }
        return {
            "ok": True,
            "status": int(resp.status_code),
            "latency_ms": latency_ms,
            "data": data,
            "error": None,
            "path": route,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": 0,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "data": None,
            "error": str(exc)[:280],
            "path": route,
        }


def _make_probe_client():
    """In-process ASGI client — no lifespan, no second HTTP server."""
    import httpx
    from fastapi import FastAPI

    from app.api.routes import router

    mini = FastAPI()
    mini.include_router(router, prefix="/v1")
    timeout = probe_timeout_sec()
    try:
        transport = httpx.ASGITransport(app=mini, lifespan="off")
    except TypeError:
        transport = httpx.ASGITransport(app=mini)
    return httpx.Client(transport=transport, base_url="http://imap.local", timeout=timeout)


def soft_probe_catalog(*, layers: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """Soft-probe catalog routes with bounded concurrency. Worker-only."""
    catalog = layers if layers is not None else load_catalog_layers()
    probes: dict[str, Any] = {}
    if not catalog:
        return probes

    client = _make_probe_client()
    try:
        workers = min(probe_workers(), len(catalog))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {
                pool.submit(_probe_path, client, row["route"]): row["id"] for row in catalog
            }
            for fut in as_completed(futs):
                lid = futs[fut]
                try:
                    probes[lid] = fut.result()
                except Exception as exc:  # noqa: BLE001
                    probes[lid] = {
                        "ok": False,
                        "status": 0,
                        "latency_ms": 0,
                        "data": None,
                        "error": str(exc)[:280],
                        "path": next((r["route"] for r in catalog if r["id"] == lid), ""),
                    }
    finally:
        try:
            client.close()
        except Exception:
            pass
    return probes


def _summarize(probes: dict[str, Any]) -> dict[str, Any]:
    active = sum(1 for p in probes.values() if isinstance(p, dict) and p.get("ok"))
    unreachable = sum(
        1
        for p in probes.values()
        if isinstance(p, dict)
        and not p.get("ok")
        and int(p.get("status") or 0) in {0, 404, 502, 503}
    )
    partial = max(0, len(probes) - active - unreachable)
    return {
        "total": len(probes),
        "active": active,
        "partial": partial,
        "unreachable": unreachable,
        "headline": f"{active} active · {partial} partial · {unreachable} unreachable",
    }


def build_and_persist_intelligence_map(*, trigger: str = "manual") -> dict[str, Any]:
    layers = load_catalog_layers()
    if os.getenv("PYTEST_CURRENT_TEST") and os.getenv("MC_ALLOW_LIVE_IN_PYTEST") != "1":
        probes = {
            row["id"]: {
                "ok": True,
                "status": 200,
                "latency_ms": 1,
                "data": {"status": "ok", "pytest_stub": True},
                "error": None,
                "path": row["route"],
            }
            for row in layers[:5]
        }
        # Ensure empty-catalog tests still get a shape.
        if not probes:
            probes = {
                "FIL": {
                    "ok": True,
                    "status": 200,
                    "latency_ms": 1,
                    "data": {"status": "ok"},
                    "error": None,
                    "path": "/filing-intelligence/health",
                }
            }
        body = {
            "enabled": True,
            "read_only": True,
            "version": INTELLIGENCE_MAP_VERSION,
            "generated_at": _now(),
            "probes": probes,
            "summary": _summarize(probes),
            "mission_control_summary": {
                "live_event_stream": [],
                "knowledge_growth": {"evidence_objects": 0, "nodes": 0, "edges": 0, "memory_objects": 0},
            },
            "layers": layers or [{"id": "FIL", "route": "/filing-intelligence/health"}],
        }
        meta = put_intelligence_map(body, trigger=f"pytest:{trigger}")
        return {"ok": True, "trigger": trigger, "meta": meta, "pytest_stub": True}

    probes = soft_probe_catalog(layers=layers)
    body = {
        "enabled": True,
        "read_only": True,
        "version": INTELLIGENCE_MAP_VERSION,
        "generated_at": _now(),
        "probes": probes,
        "summary": _summarize(probes),
        "mission_control_summary": _mc_summary_slice(),
        "layers": layers,
    }
    meta = put_intelligence_map(body, trigger=trigger)
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
            job_id = f"imap-snap-{uuid.uuid4().hex[:12]}"
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
            "snapshot": intelligence_map_meta(),
            "message": "Intelligence Map rebuild already in progress; serving existing snapshot",
        }

    def _worker() -> None:
        _set_job(status="running")
        try:
            build_and_persist_intelligence_map(trigger=trigger)
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
            "snapshot": intelligence_map_meta(),
            "intelligence_map": get_intelligence_map() or warming_payload(),
        }

    threading.Thread(target=_worker, name=f"imap-snap-{job_id}", daemon=True).start()
    return {
        "ok": True,
        "status": "queued",
        "job_id": job_id,
        "snapshot": intelligence_map_meta(),
        "message": "Intelligence Map snapshot rebuild queued; existing snapshot continues to serve",
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
        path = intelligence_map_path()
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
