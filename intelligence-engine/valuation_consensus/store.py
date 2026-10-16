"""Versioned file-backed store for valuation_consensus.

Layout under $KIP_DATA_DIR/valuation_consensus (or VALUATION_CONSENSUS_ROOT):

  live.json          — current published snapshot {version_id, updated_at, rows}
  versions/<id>.json — immutable published snapshots for rollback
  imports/<id>.json  — staged import previews (not live until publish)
  audit.jsonl        — append-only import / publish / rollback events

Excel is never the live datastore. UI and Ask read only from live.json.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_LOCK = threading.RLock()
_CACHE: dict[str, Any] | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def store_root() -> Path:
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    raw = (os.getenv("VALUATION_CONSENSUS_ROOT") or "").strip()
    if raw:
        root = Path(raw)
    elif kip:
        root = Path(kip) / "valuation_consensus"
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "valuation_consensus"
    (root / "versions").mkdir(parents=True, exist_ok=True)
    (root / "imports").mkdir(parents=True, exist_ok=True)
    return root


def _write_json(path: Path, payload: Any) -> None:
    try:
        from institutional_data.persistence.atomic import atomic_write_json, file_lock

        with file_lock(path):
            atomic_write_json(path, payload)
        return
    except Exception:
        path.parent.mkdir(parents=True, exist_ok=True)
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


def _append_audit(event: dict[str, Any]) -> None:
    path = store_root() / "audit.jsonl"
    line = json.dumps({**event, "at": _now()}, default=str)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _empty_live() -> dict[str, Any]:
    return {
        "version_id": None,
        "updated_at": None,
        "source_file": None,
        "row_count": 0,
        "rows": {},
    }


def invalidate_cache() -> None:
    global _CACHE
    with _LOCK:
        _CACHE = None


def load_live(*, force: bool = False) -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        if _CACHE is not None and not force:
            return _CACHE
        disk = _read_json(store_root() / "live.json")
        if not isinstance(disk, dict):
            _CACHE = _empty_live()
        else:
            disk.setdefault("rows", {})
            if not isinstance(disk["rows"], dict):
                disk["rows"] = {}
            _CACHE = disk
        return _CACHE


def save_live(payload: dict[str, Any]) -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        payload = dict(payload)
        rows = payload.get("rows") or {}
        if not isinstance(rows, dict):
            rows = {}
        payload["rows"] = rows
        payload["row_count"] = len(rows)
        payload["updated_at"] = _now()
        _write_json(store_root() / "live.json", payload)
        _CACHE = payload
        return payload


def get_row(ticker: str) -> Optional[dict[str, Any]]:
    t = str(ticker or "").strip().upper()
    if not t:
        return None
    live = load_live()
    row = (live.get("rows") or {}).get(t)
    return dict(row) if isinstance(row, dict) else None


def list_tickers() -> list[str]:
    return sorted((load_live().get("rows") or {}).keys())


def save_import_draft(draft: dict[str, Any]) -> dict[str, Any]:
    import_id = str(draft.get("import_id") or uuid.uuid4().hex[:12])
    draft = {**draft, "import_id": import_id, "updated_at": _now()}
    _write_json(store_root() / "imports" / f"{import_id}.json", draft)
    return draft


def load_import_draft(import_id: str) -> Optional[dict[str, Any]]:
    return _read_json(store_root() / "imports" / f"{str(import_id).strip()}.json")


def list_import_drafts(limit: int = 20) -> list[dict[str, Any]]:
    root = store_root() / "imports"
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        body = _read_json(path)
        if not isinstance(body, dict):
            continue
        items.append(
            {
                "import_id": body.get("import_id") or path.stem,
                "filename": body.get("filename"),
                "status": body.get("status"),
                "row_count": body.get("row_count"),
                "updated_at": body.get("updated_at"),
                "imported_by": body.get("imported_by"),
            }
        )
        if len(items) >= limit:
            break
    return items


def publish_rows(
    rows: dict[str, dict[str, Any]],
    *,
    source_file: str,
    imported_by: str | None,
    import_id: str | None = None,
    previous_version_id: str | None = None,
) -> dict[str, Any]:
    """Replace live snapshot with `rows`, retaining prior live as a version."""
    with _LOCK:
        live = load_live(force=True)
        old_rows = dict(live.get("rows") or {})
        version_id = uuid.uuid4().hex[:12]

        # Diff against previous live
        old_keys = set(old_rows)
        new_keys = set(rows)
        added = sorted(new_keys - old_keys)
        removed = sorted(old_keys - new_keys)
        changed: list[str] = []
        for t in sorted(old_keys & new_keys):
            a, b = old_rows.get(t) or {}, rows.get(t) or {}
            # Compare without bookkeeping noise
            skip = {"updated_at", "version_id", "source_file"}
            if {k: v for k, v in a.items() if k not in skip} != {
                k: v for k, v in b.items() if k not in skip
            }:
                changed.append(t)

        if old_rows:
            snap_id = str(live.get("version_id") or uuid.uuid4().hex[:12])
            snap = {
                **live,
                "version_id": snap_id,
                "archived_at": _now(),
                "superseded_by": version_id,
            }
            _write_json(store_root() / "versions" / f"{snap_id}.json", snap)

        stamped: dict[str, dict[str, Any]] = {}
        for t, row in rows.items():
            body = dict(row)
            body["ticker"] = t
            body["updated_at"] = _now()
            body["source_file"] = source_file
            body["version_id"] = version_id
            stamped[t] = body

        payload = {
            "version_id": version_id,
            "updated_at": _now(),
            "source_file": source_file,
            "import_id": import_id,
            "imported_by": imported_by,
            "previous_version_id": previous_version_id or live.get("version_id"),
            "row_count": len(stamped),
            "rows": stamped,
            "diff": {
                "rows_added": len(added),
                "rows_removed": len(removed),
                "rows_changed": len(changed),
                "added": added[:200],
                "removed": removed[:200],
                "changed": changed[:200],
            },
        }
        save_live(payload)
        _append_audit(
            {
                "event": "publish",
                "version_id": version_id,
                "import_id": import_id,
                "imported_by": imported_by,
                "source_file": source_file,
                "rows_added": len(added),
                "rows_removed": len(removed),
                "rows_changed": len(changed),
                "row_count": len(stamped),
                "rollback_version": payload.get("previous_version_id"),
            }
        )
        return payload


def rollback_to(version_id: str, *, actor: str | None = None) -> dict[str, Any]:
    path = store_root() / "versions" / f"{str(version_id).strip()}.json"
    snap = _read_json(path)
    if not isinstance(snap, dict) or not isinstance(snap.get("rows"), dict):
        raise ValueError(f"version_not_found:{version_id}")
    # Re-publish the archived snapshot as a new live version (keeps history).
    return publish_rows(
        {k: dict(v) for k, v in (snap.get("rows") or {}).items() if isinstance(v, dict)},
        source_file=f"rollback:{version_id}",
        imported_by=actor or "system",
        import_id=None,
        previous_version_id=version_id,
    )


def list_versions(limit: int = 30) -> list[dict[str, Any]]:
    root = store_root() / "versions"
    items: list[dict[str, Any]] = []
    live = load_live()
    if live.get("version_id"):
        items.append(
            {
                "version_id": live.get("version_id"),
                "updated_at": live.get("updated_at"),
                "source_file": live.get("source_file"),
                "row_count": live.get("row_count"),
                "live": True,
            }
        )
    for path in sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        body = _read_json(path)
        if not isinstance(body, dict):
            continue
        items.append(
            {
                "version_id": body.get("version_id") or path.stem,
                "updated_at": body.get("updated_at") or body.get("archived_at"),
                "source_file": body.get("source_file"),
                "row_count": body.get("row_count") or len(body.get("rows") or {}),
                "live": False,
            }
        )
        if len(items) >= limit:
            break
    return items


def read_audit(limit: int = 50) -> list[dict[str, Any]]:
    path = store_root() / "audit.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[dict[str, Any]] = []
    for line in reversed(lines[-limit:]):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
