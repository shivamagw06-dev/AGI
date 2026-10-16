"""Validated Knowledge Store — file-backed, auditable, no raw-API leakage."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

STORE_VERSION = "kf-store-v1.0.0"

_LOCK = threading.Lock()
_DEFAULT_ROOT = Path(
    os.environ.get(
        "KF_STORE_ROOT",
        str(Path(__file__).resolve().parents[2] / "data" / "knowledge_factory"),
    )
)


def store_root() -> Path:
    root = Path(_DEFAULT_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    (root / "raw").mkdir(exist_ok=True)
    (root / "validated").mkdir(exist_ok=True)
    (root / "objects").mkdir(exist_ok=True)
    (root / "packs").mkdir(exist_ok=True)
    (root / "reports").mkdir(exist_ok=True)
    return root


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def put_raw(source: str, entity: str, dataset: dict[str, Any]) -> str:
    root = store_root() / "raw" / source
    key = f"{entity.upper()}_{int(time.time())}.json"
    path = root / key
    with _LOCK:
        _write_json(path, dataset)
    return str(path)


def put_validated(kind: str, entity: str, dataset: dict[str, Any]) -> str:
    root = store_root() / "validated" / kind
    path = root / f"{entity.upper()}.json"
    with _LOCK:
        _write_json(
            path,
            {
                **dataset,
                "store_version": STORE_VERSION,
                "published": True,
                "entity": entity.upper() if entity else None,
            },
        )
    return str(path)


def get_validated(kind: str, entity: str) -> dict[str, Any] | None:
    path = store_root() / "validated" / kind / f"{entity.upper()}.json"
    return _read_json(path)


def put_object(kind: str, entity: str, obj: dict[str, Any]) -> str:
    path = store_root() / "objects" / kind / f"{entity.upper()}.json"
    with _LOCK:
        _write_json(path, obj)
    return str(path)


def get_object(kind: str, entity: str) -> dict[str, Any] | None:
    path = store_root() / "objects" / kind / f"{entity.upper()}.json"
    return _read_json(path)


def list_objects(kind: str) -> list[str]:
    root = store_root() / "objects" / kind
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.json"))


def put_report(name: str, report: dict[str, Any]) -> str:
    path = store_root() / "reports" / f"{name}.json"
    with _LOCK:
        _write_json(path, report)
    return str(path)


def get_report(name: str) -> dict[str, Any] | None:
    return _read_json(store_root() / "reports" / f"{name}.json")


def put_pack(entity: str, pack: dict[str, Any]) -> str:
    path = store_root() / "packs" / f"{entity.upper()}.json"
    with _LOCK:
        _write_json(path, pack)
    return str(path)


def get_pack(entity: str) -> dict[str, Any] | None:
    return _read_json(store_root() / "packs" / f"{entity.upper()}.json")


def reset_store() -> None:
    """Test helper — wipe validated/objects/packs/reports (keep fixtures)."""
    root = store_root()
    with _LOCK:
        for sub in ("validated", "objects", "packs", "reports", "raw"):
            d = root / sub
            if d.exists():
                for p in d.rglob("*.json"):
                    try:
                        p.unlink()
                    except Exception:
                        pass
