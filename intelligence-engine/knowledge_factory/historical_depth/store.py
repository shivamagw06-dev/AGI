"""Append-only Historical Knowledge Store.

Never overwrites history. Point-in-time reads filter on available_from.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from knowledge_factory.historical_depth.schema import HD_VERSION

_LOCK = threading.Lock()


def hd_root() -> Path:
    """Durable root — prefers KF_HD_STORE_ROOT, else KIP_DATA_DIR/historical_depth."""
    raw = (os.environ.get("KF_HD_STORE_ROOT") or "").strip()
    if not raw:
        kip = (os.environ.get("KIP_DATA_DIR") or "").strip()
        if kip:
            raw = str(Path(kip) / "historical_depth")
        else:
            raw = str(Path(__file__).resolve().parents[2] / "data" / "knowledge_factory" / "historical")
    root = Path(raw)
    for sub in (
        "prices",
        "financials_annual",
        "financials_quarterly",
        "corporate_actions",
        "shareholding",
        "timeline",
        "regimes",
        "macro",
        "derived",
        "objects",
        "packs",
        "reports",
    ):
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


def _read(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def put_series(kind: str, entity: str, records: list[dict[str, Any]]) -> str:
    """Replace entity series file only when extending (append-merge by period)."""
    path = hd_root() / kind / f"{entity.upper()}.json"
    with _LOCK:
        existing = _read(path) or {"entity": entity.upper(), "kind": kind, "records": [], "hd_version": HD_VERSION}
        by_key: dict[str, dict[str, Any]] = {}
        for r in existing.get("records") or []:
            key = f"{r.get('period')}|{r.get('available_from')}|{r.get('kind')}"
            by_key[key] = r
        for r in records:
            key = f"{r.get('period')}|{r.get('available_from')}|{r.get('kind')}"
            # Never overwrite an existing immutable record — keep first write.
            if key not in by_key:
                by_key[key] = r
        merged = sorted(by_key.values(), key=lambda x: (str(x.get("period_end") or ""), str(x.get("available_from") or "")))
        payload = {
            "entity": entity.upper(),
            "kind": kind,
            "records": merged,
            "hd_version": HD_VERSION,
            "n": len(merged),
        }
        _write(path, payload)
    return str(path)


def get_series(kind: str, entity: str) -> dict[str, Any] | None:
    return _read(hd_root() / kind / f"{entity.upper()}.json")


def put_regimes(regimes: list[dict[str, Any]]) -> str:
    path = hd_root() / "regimes" / "MARKET.json"
    with _LOCK:
        existing = _read(path) or {"regimes": []}
        by_id = {r["regime_id"]: r for r in existing.get("regimes") or []}
        for r in regimes:
            by_id.setdefault(r["regime_id"], r)
        payload = {"hd_version": HD_VERSION, "regimes": list(by_id.values())}
        _write(path, payload)
    return str(path)


def get_regimes() -> list[dict[str, Any]]:
    data = _read(hd_root() / "regimes" / "MARKET.json") or {}
    return list(data.get("regimes") or [])


def put_macro_history(records: list[dict[str, Any]]) -> str:
    path = hd_root() / "macro" / "GLOBAL.json"
    with _LOCK:
        existing = _read(path) or {"records": []}
        by_p = {r["period"]: r for r in existing.get("records") or []}
        for r in records:
            by_p.setdefault(r["period"], r)
        payload = {
            "hd_version": HD_VERSION,
            "records": sorted(by_p.values(), key=lambda x: x["period"]),
        }
        _write(path, payload)
    return str(path)


def get_macro_history() -> list[dict[str, Any]]:
    data = _read(hd_root() / "macro" / "GLOBAL.json") or {}
    return list(data.get("records") or [])


def put_object(kind: str, entity: str, obj: dict[str, Any]) -> str:
    path = hd_root() / "objects" / kind / f"{entity.upper()}.json"
    with _LOCK:
        _write(path, {**obj, "hd_version": HD_VERSION})
    return str(path)


def get_object(kind: str, entity: str) -> dict[str, Any] | None:
    return _read(hd_root() / "objects" / kind / f"{entity.upper()}.json")


def list_objects(kind: str) -> list[str]:
    root = hd_root() / "objects" / kind
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.json"))


def put_pack(entity: str, pack: dict[str, Any]) -> str:
    path = hd_root() / "packs" / f"{entity.upper()}.json"
    with _LOCK:
        _write(path, {**pack, "hd_version": HD_VERSION})
    return str(path)


def get_pack(entity: str) -> dict[str, Any] | None:
    return _read(hd_root() / "packs" / f"{entity.upper()}.json")


def put_report(name: str, report: dict[str, Any]) -> str:
    path = hd_root() / "reports" / f"{name}.json"
    with _LOCK:
        _write(path, {**report, "hd_version": HD_VERSION})
    return str(path)


def get_report(name: str) -> dict[str, Any] | None:
    return _read(hd_root() / "reports" / f"{name}.json")


def reset_store() -> None:
    """Test helper — wipe historical store."""
    import shutil

    root = hd_root()
    with _LOCK:
        if root.exists():
            shutil.rmtree(root)
        hd_root()


def filter_pit(records: list[dict[str, Any]], as_of: str) -> list[dict[str, Any]]:
    """Point-in-time integrity: keep only records available on or before as_of."""
    return [r for r in records if str(r.get("available_from") or "") <= as_of]
