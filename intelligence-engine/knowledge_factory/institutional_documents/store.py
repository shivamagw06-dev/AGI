"""IDI file-backed store — documents, chunks, objects, packs, replay."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_DEFAULT = Path(
    os.environ.get(
        "IDI_STORE_ROOT",
        str(Path(__file__).resolve().parents[1] / "data" / "institutional_documents"),
    )
)

_DOCS: dict[str, dict[str, Any]] = {}
_CHUNKS: dict[str, list[dict[str, Any]]] = {}
_OBJECTS: dict[str, dict[str, Any]] = {}
_PACKS: dict[str, dict[str, Any]] = {}
_RUNS: list[dict[str, Any]] = []
_VALIDATION_LOG: list[dict[str, Any]] = []


def reset() -> None:
    _DOCS.clear()
    _CHUNKS.clear()
    _OBJECTS.clear()
    _PACKS.clear()
    _RUNS.clear()
    _VALIDATION_LOG.clear()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def store_root() -> Path:
    root = Path(os.environ.get("IDI_STORE_ROOT", str(_DEFAULT)))
    for sub in ("raw", "documents", "chunks", "objects", "packs", "reports", "timeline"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def checksum_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def put_document(doc: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(doc["document_id"])
    with _LOCK:
        _DOCS[doc_id] = deepcopy(doc)
        _write(store_root() / "documents" / f"{doc_id}.json", doc)
    return deepcopy(doc)


def get_document(doc_id: str) -> dict[str, Any] | None:
    if doc_id in _DOCS:
        return deepcopy(_DOCS[doc_id])
    path = store_root() / "documents" / f"{doc_id}.json"
    if path.exists():
        row = json.loads(path.read_text(encoding="utf-8"))
        _DOCS[doc_id] = row
        return deepcopy(row)
    return None


def list_documents(*, ticker: str | None = None, doc_type: str | None = None) -> list[dict[str, Any]]:
    # hydrate from disk
    for p in store_root().glob("documents/*.json"):
        if p.stem not in _DOCS:
            try:
                _DOCS[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    rows = list(_DOCS.values())
    if ticker:
        t = ticker.upper()
        rows = [r for r in rows if str(r.get("company") or "").upper() == t]
    if doc_type:
        rows = [r for r in rows if r.get("type") == doc_type]
    rows.sort(key=lambda r: str(r.get("published_date") or ""), reverse=True)
    return deepcopy(rows)


def put_chunks(doc_id: str, chunks: list[dict[str, Any]]) -> None:
    with _LOCK:
        _CHUNKS[doc_id] = deepcopy(chunks)
        _write(store_root() / "chunks" / f"{doc_id}.json", {"document_id": doc_id, "chunks": chunks})


def get_chunks(doc_id: str) -> list[dict[str, Any]]:
    if doc_id in _CHUNKS:
        return deepcopy(_CHUNKS[doc_id])
    path = store_root() / "chunks" / f"{doc_id}.json"
    if path.exists():
        row = json.loads(path.read_text(encoding="utf-8"))
        _CHUNKS[doc_id] = list(row.get("chunks") or [])
        return deepcopy(_CHUNKS[doc_id])
    return []


def put_object(obj_id: str, obj: dict[str, Any]) -> None:
    with _LOCK:
        _OBJECTS[obj_id] = deepcopy(obj)
        _write(store_root() / "objects" / f"{obj_id}.json", obj)


def list_objects(*, ticker: str | None = None) -> list[dict[str, Any]]:
    for p in store_root().glob("objects/*.json"):
        if p.stem not in _OBJECTS:
            try:
                _OBJECTS[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    rows = list(_OBJECTS.values())
    if ticker:
        t = ticker.upper()
        rows = [r for r in rows if str(r.get("company") or "").upper() == t]
    return deepcopy(rows)


def put_pack(pack_id: str, pack: dict[str, Any]) -> None:
    with _LOCK:
        _PACKS[pack_id] = deepcopy(pack)
        _write(store_root() / "packs" / f"{pack_id}.json", pack)


def list_packs(*, ticker: str | None = None) -> list[dict[str, Any]]:
    for p in store_root().glob("packs/*.json"):
        if p.stem not in _PACKS:
            try:
                _PACKS[p.stem] = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    rows = list(_PACKS.values())
    if ticker:
        t = ticker.upper()
        rows = [r for r in rows if str(r.get("company") or "").upper() == t]
    return deepcopy(rows)


def record_run(report: dict[str, Any]) -> None:
    _RUNS.append(deepcopy(report))
    _RUNS[:] = _RUNS[-100:]
    _write(store_root() / "reports" / "last_run.json", report)


def last_run() -> dict[str, Any] | None:
    if _RUNS:
        return deepcopy(_RUNS[-1])
    path = store_root() / "reports" / "last_run.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def log_validation(row: dict[str, Any]) -> None:
    _VALIDATION_LOG.append({**row, "at": utc_now()})
    _VALIDATION_LOG[:] = _VALIDATION_LOG[-200:]


def list_validations(*, limit: int = 50) -> list[dict[str, Any]]:
    return deepcopy(list(reversed(_VALIDATION_LOG[-max(1, limit) :])))


def put_raw(name: str, text: str, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    data = text.encode("utf-8")
    path = store_root() / "raw" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    rec = {
        "path": str(path),
        "name": name,
        "checksum": checksum_bytes(data),
        "bytes": len(data),
        "stored_at": utc_now(),
        "meta": meta or {},
    }
    _write(path.with_suffix(path.suffix + ".meta.json"), rec)
    return rec
