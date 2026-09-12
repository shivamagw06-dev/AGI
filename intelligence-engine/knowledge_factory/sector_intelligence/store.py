"""Append-friendly Institutional Sector Intelligence store."""

from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any

from knowledge_factory.sector_intelligence.schema import ISI_VERSION

_LOCK = threading.Lock()
_DEFAULT = Path(
    os.environ.get(
        "KF_ISI_STORE_ROOT",
        str(Path(__file__).resolve().parents[2] / "data" / "knowledge_factory" / "sectors"),
    )
)


def isi_root() -> Path:
    root = Path(_DEFAULT)
    for sub in ("objects", "packs", "rankings", "cycles", "reports", "timelines"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _read(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def put_object(sector: str, obj: dict[str, Any]) -> str:
    path = isi_root() / "objects" / f"{sector}.json"
    with _LOCK:
        _write(path, {**obj, "isi_version": ISI_VERSION})
    return str(path)


def get_object(sector: str) -> dict[str, Any] | None:
    return _read(isi_root() / "objects" / f"{sector}.json")


def list_objects() -> list[str]:
    root = isi_root() / "objects"
    return sorted(p.stem for p in root.glob("*.json"))


def put_pack(sector: str, pack: dict[str, Any]) -> str:
    path = isi_root() / "packs" / f"{sector}.json"
    with _LOCK:
        _write(path, {**pack, "isi_version": ISI_VERSION})
    return str(path)


def get_pack(sector: str) -> dict[str, Any] | None:
    return _read(isi_root() / "packs" / f"{sector}.json")


def put_rankings(payload: dict[str, Any]) -> str:
    path = isi_root() / "rankings" / "CROSS_SECTOR.json"
    with _LOCK:
        _write(path, {**payload, "isi_version": ISI_VERSION})
    return str(path)


def get_rankings() -> dict[str, Any] | None:
    return _read(isi_root() / "rankings" / "CROSS_SECTOR.json")


def put_report(name: str, report: dict[str, Any]) -> str:
    path = isi_root() / "reports" / f"{name}.json"
    with _LOCK:
        _write(path, {**report, "isi_version": ISI_VERSION})
    return str(path)


def get_report(name: str) -> dict[str, Any] | None:
    return _read(isi_root() / "reports" / f"{name}.json")


def put_timeline(sector: str, events: list[dict[str, Any]]) -> str:
    path = isi_root() / "timelines" / f"{sector}.json"
    with _LOCK:
        _write(path, {"sector": sector, "events": events, "isi_version": ISI_VERSION})
    return str(path)


def get_timeline(sector: str) -> list[dict[str, Any]]:
    data = _read(isi_root() / "timelines" / f"{sector}.json") or {}
    return list(data.get("events") or [])


def reset_store() -> None:
    root = isi_root()
    with _LOCK:
        if root.exists():
            shutil.rmtree(root)
        isi_root()
