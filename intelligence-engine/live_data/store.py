"""LIDI file-backed store — raw, validated snapshots, collector health, never KF fixtures."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()

_HEALTH: dict[str, dict[str, Any]] = {}
_VALIDATION_LOG: list[dict[str, Any]] = []
_FALLBACK_LOG: list[dict[str, Any]] = []
_LAST_RUN: dict[str, Any] | None = None


def reset_runtime() -> None:
    global _LAST_RUN
    _HEALTH.clear()
    _VALIDATION_LOG.clear()
    _FALLBACK_LOG.clear()
    _LAST_RUN = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def store_root() -> Path:
    raw = (os.environ.get("LIDI_STORE_ROOT") or "").strip()
    if not raw:
        kip = (os.environ.get("KIP_DATA_DIR") or "").strip()
        if kip:
            raw = str(Path(kip) / "live_data")
        else:
            raw = str(Path(__file__).resolve().parents[1] / "data" / "live_data")
    root = Path(raw)
    for sub in ("raw", "validated", "snapshots", "objects", "packs", "files", "reports", "health"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _write(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from institutional_data.persistence.atomic import atomic_write_json, file_lock

        with file_lock(path):
            atomic_write_json(path, payload)
        return
    except Exception:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str, sort_keys=True), encoding="utf-8")
        tmp.replace(path)


def _read(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def put_raw_file(source_id: str, name: str, data: bytes, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    root = store_root() / "files" / source_id
    root.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    path = root / f"{ts}_{name}"
    with _LOCK:
        path.write_bytes(data)
        rec = {
            "path": str(path),
            "source_id": source_id,
            "name": name,
            "checksum": checksum_bytes(data),
            "bytes": len(data),
            "stored_at": utc_now(),
            "meta": meta or {},
        }
        _write(root / f"{ts}_{name}.meta.json", rec)
    return rec


def put_raw(source_id: str, entity: str, dataset: dict[str, Any]) -> str:
    path = store_root() / "raw" / source_id / f"{entity}_{int(time.time())}.json"
    with _LOCK:
        _write(path, dataset)
    return str(path)


def put_validated(source_id: str, entity: str, dataset: dict[str, Any]) -> str:
    path = store_root() / "validated" / source_id / f"{entity.upper()}.json"
    snap = store_root() / "snapshots" / source_id / f"{entity.upper()}.json"
    payload = {**dataset, "entity": entity.upper(), "validated_store_path": str(path)}
    with _LOCK:
        _write(path, payload)
        _write(snap, payload)  # latest validated snapshot for fallback
    return str(path)


def get_validated(source_id: str, entity: str) -> dict[str, Any] | None:
    return _read(store_root() / "validated" / source_id / f"{entity.upper()}.json")


def get_latest_snapshot(source_id: str, entity: str = "LATEST") -> dict[str, Any] | None:
    row = _read(store_root() / "snapshots" / source_id / f"{entity.upper()}.json")
    if row:
        return row
    root = store_root() / "snapshots" / source_id
    if not root.exists():
        return None
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return _read(files[0]) if files else None


def put_object(kind: str, entity: str, obj: dict[str, Any]) -> str:
    path = store_root() / "objects" / kind / f"{entity.upper()}.json"
    with _LOCK:
        _write(path, obj)
    return str(path)


def get_object(kind: str, entity: str) -> dict[str, Any] | None:
    return _read(store_root() / "objects" / kind / f"{entity.upper()}.json")


def write_objects(as_of: str, objects: dict[str, list[dict[str, Any]]]) -> str:
    path = store_root() / "objects" / f"bundle_{as_of}.json"
    with _LOCK:
        _write(path, {"as_of": as_of, "objects": objects, "written_at": utc_now()})
        for kind, rows in objects.items():
            for i, obj in enumerate(rows[:200]):
                key = str(obj.get("ticker") or obj.get("series_id") or obj.get("pack_id") or i)
                safe = f"{as_of}_{key}"[:80].upper()
                _write(store_root() / "objects" / kind / f"{safe}.json", obj)
    return str(path)


def put_pack(entity: str, pack: dict[str, Any]) -> str:
    path = store_root() / "packs" / f"{entity.upper()}.json"
    with _LOCK:
        _write(path, pack)
    return str(path)


def write_evidence_packs(as_of: str, packs: list[dict[str, Any]]) -> str:
    path = store_root() / "packs" / f"bundle_{as_of}.json"
    with _LOCK:
        _write(path, {"as_of": as_of, "packs": packs, "written_at": utc_now()})
        for p in packs:
            entity = str(p.get("pack_id") or f"pack_{as_of}").upper()
            _write(store_root() / "packs" / f"{entity}.json", p)
    return str(path)


def get_pack(entity: str) -> dict[str, Any] | None:
    return _read(store_root() / "packs" / f"{entity.upper()}.json")


def update_collector_health(collector_id: str, **kwargs: Any) -> dict[str, Any]:
    row = _HEALTH.get(collector_id) or {
        "collector_id": collector_id,
        "last_success": None,
        "last_failure": None,
        "success_count": 0,
        "failure_count": 0,
        "last_checksum": None,
        "downloaded_files": [],
    }
    row.update(kwargs)
    _HEALTH[collector_id] = row
    _write(store_root() / "health" / f"{collector_id}.json", row)
    return deepcopy(row)


def get_collector_health(collector_id: str | None = None) -> dict[str, Any]:
    if collector_id:
        path = store_root() / "health" / f"{collector_id}.json"
        return _read(path) or _HEALTH.get(collector_id) or {}
    out = {}
    root = store_root() / "health"
    for p in root.glob("*.json"):
        out[p.stem] = _read(p)
    out.update({k: v for k, v in _HEALTH.items() if k not in out})
    return deepcopy(out)


def log_validation(row: dict[str, Any]) -> None:
    _VALIDATION_LOG.append({**row, "at": utc_now()})
    _VALIDATION_LOG[:] = _VALIDATION_LOG[-200:]


def list_validations(*, limit: int = 50) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_VALIDATION_LOG[-max(1, limit) :])))


def log_fallback(row: dict[str, Any]) -> None:
    _FALLBACK_LOG.append({**row, "at": utc_now()})
    _FALLBACK_LOG[:] = _FALLBACK_LOG[-200:]


def list_fallbacks(*, limit: int = 50) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_FALLBACK_LOG[-max(1, limit) :])))


def put_report(name: str, report: dict[str, Any]) -> str:
    path = store_root() / "reports" / f"{name}.json"
    with _LOCK:
        _write(path, report)
    return str(path)


def get_report(name: str) -> dict[str, Any] | None:
    return _read(store_root() / "reports" / f"{name}.json")


def set_last_run(report: dict[str, Any]) -> None:
    global _LAST_RUN
    _LAST_RUN = deepcopy(report)
    put_report("last_run", report)


def get_last_run() -> dict[str, Any] | None:
    if _LAST_RUN:
        return deepcopy(_LAST_RUN)
    return get_report("last_run")
