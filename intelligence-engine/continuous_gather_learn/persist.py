"""Disk persistence for CGL checkpoints, metrics, and institutional learning archive.

Survives process restarts when CGL_STORE_ROOT or KIP_DATA_DIR is on durable disk.
Never blocks Ask — all writes are best-effort.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()


def store_root() -> Path:
    raw = (
        os.getenv("CGL_STORE_ROOT")
        or (os.getenv("KIP_DATA_DIR") and str(Path(os.getenv("KIP_DATA_DIR")) / "continuous_gather_learn"))
        or ""
    ).strip()
    if raw:
        root = Path(raw)
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "continuous_gather_learn"
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("checkpoints", "learnings", "metrics", "runs", "knowledge", "embeddings"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def get_checkpoint(name: str) -> dict[str, Any]:
    with _LOCK:
        return _read_json(store_root() / "checkpoints" / f"{name}.json", {}) or {}


def put_checkpoint(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    with _LOCK:
        body = {**(payload or {}), "updated_at": _now(), "checkpoint": name}
        _write_json(store_root() / "checkpoints" / f"{name}.json", body)
        return body


def archive_learning(learning: dict[str, Any]) -> str:
    """Append-only durable learning archive (ILO/FVL soft mirror)."""
    with _LOCK:
        lid = str(
            learning.get("learning_id")
            or learning.get("id")
            or f"cgl_{int(time.time() * 1000)}"
        )
        path = store_root() / "learnings" / f"{lid}.json"
        body = {**learning, "learning_id": lid, "archived_at": _now(), "durable": True}
        _write_json(path, body)
        # Rolling index
        index_path = store_root() / "learnings" / "_index.json"
        index = _read_json(index_path, {"ids": []}) or {"ids": []}
        ids = list(index.get("ids") or [])
        if lid not in ids:
            ids.insert(0, lid)
        index = {"ids": ids[:2000], "updated_at": _now(), "count": len(ids[:2000])}
        _write_json(index_path, index)
        return lid


def list_archived_learnings(*, limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        index = _read_json(store_root() / "learnings" / "_index.json", {"ids": []}) or {}
        out: list[dict[str, Any]] = []
        for lid in list(index.get("ids") or [])[:limit]:
            row = _read_json(store_root() / "learnings" / f"{lid}.json")
            if row:
                out.append(row)
        return out


def put_run(run: dict[str, Any]) -> None:
    with _LOCK:
        rid = str(run.get("run_id") or f"run_{int(time.time())}")
        _write_json(store_root() / "runs" / f"{rid}.json", {**run, "run_id": rid})
        latest = store_root() / "metrics" / "latest_run.json"
        _write_json(latest, run)


def get_latest_run() -> dict[str, Any]:
    with _LOCK:
        return _read_json(store_root() / "metrics" / "latest_run.json", {}) or {}


def put_metrics(metrics: dict[str, Any]) -> None:
    with _LOCK:
        body = {**(metrics or {}), "updated_at": _now()}
        _write_json(store_root() / "metrics" / "observability.json", body)


def get_metrics() -> dict[str, Any]:
    with _LOCK:
        return _read_json(store_root() / "metrics" / "observability.json", {}) or {}


def put_knowledge_extract(entity: str, payload: dict[str, Any]) -> None:
    with _LOCK:
        key = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(entity or "unknown"))[:80]
        _write_json(
            store_root() / "knowledge" / f"{key}.json",
            {**payload, "entity": entity, "updated_at": _now()},
        )


def get_knowledge_extract(entity: str) -> dict[str, Any]:
    with _LOCK:
        key = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(entity or "unknown"))[:80]
        return _read_json(store_root() / "knowledge" / f"{key}.json", {}) or {}


def put_embedding(entity: str, payload: dict[str, Any]) -> None:
    """Store structured knowledge embedding (deterministic hash vector — not ML training)."""
    with _LOCK:
        key = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(entity or "unknown"))[:80]
        _write_json(
            store_root() / "embeddings" / f"{key}.json",
            {**payload, "entity": entity, "updated_at": _now()},
        )


def get_embedding(entity: str) -> dict[str, Any]:
    with _LOCK:
        key = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(entity or "unknown"))[:80]
        return _read_json(store_root() / "embeddings" / f"{key}.json", {}) or {}


def count_embeddings() -> int:
    with _LOCK:
        root = store_root() / "embeddings"
        return len([p for p in root.glob("*.json") if p.is_file()])


def count_knowledge_extracts() -> int:
    with _LOCK:
        root = store_root() / "knowledge"
        return len([p for p in root.glob("*.json") if p.is_file()])


def write_gather_heartbeat(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sidecar/worker heartbeat so HTTP health can see gather is alive on shared disk."""
    with _LOCK:
        body = {
            "role": os.getenv("AGI_ROLE") or "gather_worker",
            "pid": os.getpid(),
            "beat_at": _now(),
            "unix_ts": time.time(),
            "CONTINUOUS_GATHER_LEARN": os.getenv("CONTINUOUS_GATHER_LEARN"),
            "FAA_BACKGROUND_COLLECTOR": os.getenv("FAA_BACKGROUND_COLLECTOR"),
            "FAA_LIVE_FETCH": os.getenv("FAA_LIVE_FETCH"),
            "CONTINUOUS_LIDI": os.getenv("CONTINUOUS_LIDI"),
            "CONTINUOUS_HISTORICAL_BACKFILL": os.getenv("CONTINUOUS_HISTORICAL_BACKFILL"),
            "KF_HD_LIVE_COLLECTORS": os.getenv("KF_HD_LIVE_COLLECTORS"),
            **(payload or {}),
        }
        _write_json(store_root() / "metrics" / "gather_heartbeat.json", body)
        return body


def write_remote_gather_heartbeat(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persist an authenticated worker heartbeat using server-owned timestamps."""
    incoming = payload if isinstance(payload, dict) else {}
    allowed = {
        "phase",
        "role",
        "worker_id",
        "CONTINUOUS_GATHER_LEARN",
        "FAA_BACKGROUND_COLLECTOR",
        "FAA_LIVE_FETCH",
        "CONTINUOUS_LIDI",
        "CONTINUOUS_HISTORICAL_BACKFILL",
        "KF_HD_LIVE_COLLECTORS",
        "forecast_runtime",
        "answer_pack_materializer",
    }
    body = {key: incoming.get(key) for key in allowed if key in incoming}
    runtime = body.get("forecast_runtime")
    if isinstance(runtime, dict):
        runtime_allowed = {
            "status", "started_at", "last_tick", "last_error",
            "completed_this_session", "failed_this_session",
            "processed_this_session", "outcomes_evaluated_this_session",
            "vintages_repaired_this_session", "strategy_validations_this_session",
            "last_batch", "process_role", "owned_here",
        }
        body["forecast_runtime"] = {
            key: runtime.get(key) for key in runtime_allowed if key in runtime
        }
    else:
        body.pop("forecast_runtime", None)
    answer_pack = body.get("answer_pack_materializer")
    if isinstance(answer_pack, dict):
        answer_pack_allowed = {
            "status",
            "ok",
            "attempted",
            "written",
            "unchanged",
            "next_cursor",
            "generated_at",
            "error",
        }
        body["answer_pack_materializer"] = {
            key: answer_pack.get(key) for key in answer_pack_allowed if key in answer_pack
        }
    else:
        body.pop("answer_pack_materializer", None)
    body.update(
        {
            "role": str(body.get("role") or "gather_worker")[:80],
            "phase": str(body.get("phase") or "running")[:80],
            "source": "authenticated_remote_worker",
            "beat_at": _now(),
            "unix_ts": time.time(),
        }
    )
    with _LOCK:
        _write_json(store_root() / "metrics" / "gather_heartbeat.json", body)
    return body


def read_gather_heartbeat(*, max_age_sec: float = 180.0) -> dict[str, Any]:
    """Return gather heartbeat; mark fresh when beat is within max_age_sec."""
    with _LOCK:
        row = _read_json(store_root() / "metrics" / "gather_heartbeat.json", {}) or {}
    if not isinstance(row, dict) or not row:
        return {"fresh": False, "present": False}
    try:
        ts = float(row.get("unix_ts") or 0)
    except (TypeError, ValueError):
        ts = 0.0
    age = (time.time() - ts) if ts else None
    fresh = bool(age is not None and age >= 0 and age <= float(max_age_sec))
    return {
        **row,
        "present": True,
        "fresh": fresh,
        "age_sec": round(age, 1) if age is not None else None,
        "max_age_sec": float(max_age_sec),
    }
