"""Append-friendly Institutional Macro Intelligence store."""

from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any

from knowledge_factory.macro_intelligence.schema import IMI_VERSION

_LOCK = threading.Lock()
_DEFAULT = Path(
    os.environ.get(
        "KF_IMI_STORE_ROOT",
        str(Path(__file__).resolve().parents[2] / "data" / "knowledge_factory" / "macro"),
    )
)


def imi_root() -> Path:
    root = Path(_DEFAULT)
    for sub in ("objects", "packs", "regimes", "links", "reports", "history"):
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


def put_object(macro_id: str, obj: dict[str, Any]) -> str:
    path = imi_root() / "objects" / f"{macro_id}.json"
    with _LOCK:
        _write(path, {**obj, "imi_version": IMI_VERSION})
    return str(path)


def get_object(macro_id: str) -> dict[str, Any] | None:
    return _read(imi_root() / "objects" / f"{macro_id}.json")


def list_objects() -> list[str]:
    return sorted(p.stem for p in (imi_root() / "objects").glob("*.json"))


def put_pack(name: str, pack: dict[str, Any]) -> str:
    path = imi_root() / "packs" / f"{name}.json"
    with _LOCK:
        _write(path, {**pack, "imi_version": IMI_VERSION})
    return str(path)


def get_pack(name: str) -> dict[str, Any] | None:
    return _read(imi_root() / "packs" / f"{name}.json")


def put_regimes(payload: dict[str, Any]) -> str:
    path = imi_root() / "regimes" / "STATE.json"
    with _LOCK:
        _write(path, {**payload, "imi_version": IMI_VERSION})
    return str(path)


def get_regimes() -> dict[str, Any] | None:
    return _read(imi_root() / "regimes" / "STATE.json")


def put_links(kind: str, payload: dict[str, Any]) -> str:
    path = imi_root() / "links" / f"{kind}.json"
    with _LOCK:
        _write(path, {**payload, "imi_version": IMI_VERSION})
    return str(path)


def get_links(kind: str) -> dict[str, Any] | None:
    return _read(imi_root() / "links" / f"{kind}.json")


def put_history(series_id: str, records: list[dict[str, Any]]) -> str:
    path = imi_root() / "history" / f"{series_id}.json"
    with _LOCK:
        existing = _read(path) or {"records": []}
        by_p = {r.get("period"): r for r in existing.get("records") or []}
        for r in records:
            by_p.setdefault(r.get("period"), r)
        _write(
            path,
            {
                "series_id": series_id,
                "records": sorted(by_p.values(), key=lambda x: str(x.get("period") or "")),
                "imi_version": IMI_VERSION,
            },
        )
    return str(path)


def get_history(series_id: str) -> list[dict[str, Any]]:
    data = _read(imi_root() / "history" / f"{series_id}.json") or {}
    return list(data.get("records") or [])


def put_report(name: str, report: dict[str, Any]) -> str:
    path = imi_root() / "reports" / f"{name}.json"
    with _LOCK:
        _write(path, {**report, "imi_version": IMI_VERSION})
    return str(path)


def get_report(name: str) -> dict[str, Any] | None:
    return _read(imi_root() / "reports" / f"{name}.json")


def reset_store() -> None:
    root = imi_root()
    with _LOCK:
        if root.exists():
            shutil.rmtree(root)
        imi_root()


def filter_pit(records: list[dict[str, Any]], as_of: str) -> list[dict[str, Any]]:
    return [r for r in records if str(r.get("available_from") or r.get("period_end") or "") <= as_of]
