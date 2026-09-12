"""IUI persistent store — versioned universe snapshots + registries."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

_ROOT: Path | None = None


def iui_root() -> Path:
    global _ROOT
    if _ROOT is not None:
        return _ROOT
    env = os.environ.get("IUI_STORE_ROOT")
    if env:
        _ROOT = Path(env)
    else:
        try:
            from knowledge_factory.store import repository as kf

            _ROOT = kf.store_root().parent / "universe_intelligence"
        except Exception:
            _ROOT = Path(__file__).resolve().parents[1] / "data" / "universe_intelligence"
    _ROOT.mkdir(parents=True, exist_ok=True)
    return _ROOT


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _read(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def put_universe(universe_id: str, obj: dict[str, Any]) -> str:
    path = iui_root() / "universes" / f"{universe_id.upper()}.json"
    _write(path, obj)
    return str(path)


def get_universe(universe_id: str) -> dict[str, Any] | None:
    return _read(iui_root() / "universes" / f"{universe_id.upper()}.json")


def list_universes() -> list[str]:
    d = iui_root() / "universes"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def put_company(ticker: str, obj: dict[str, Any]) -> str:
    path = iui_root() / "companies" / f"{ticker.upper()}.json"
    _write(path, obj)
    return str(path)


def get_company(ticker: str) -> dict[str, Any] | None:
    return _read(iui_root() / "companies" / f"{ticker.upper()}.json")


def list_companies() -> list[str]:
    d = iui_root() / "companies"
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json"))


def put_membership_event(event_id: str, obj: dict[str, Any]) -> str:
    path = iui_root() / "membership_events" / f"{event_id}.json"
    _write(path, obj)
    return str(path)


def list_membership_events() -> list[dict[str, Any]]:
    d = iui_root() / "membership_events"
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*.json")):
        obj = _read(p)
        if obj:
            out.append(obj)
    return out


def put_snapshot(universe_id: str, version: str, obj: dict[str, Any]) -> str:
    path = iui_root() / "snapshots" / universe_id.upper() / f"{version}.json"
    _write(path, obj)
    # pointer to latest
    _write(iui_root() / "snapshots" / universe_id.upper() / "_latest.json", {"version": version})
    return str(path)


def get_snapshot(universe_id: str, version: str | None = None) -> dict[str, Any] | None:
    u = universe_id.upper()
    if version is None:
        latest = _read(iui_root() / "snapshots" / u / "_latest.json") or {}
        version = latest.get("version")
    if not version:
        return None
    return _read(iui_root() / "snapshots" / u / f"{version}.json")


def list_snapshots(universe_id: str) -> list[str]:
    d = iui_root() / "snapshots" / universe_id.upper()
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.json") if p.stem != "_latest")


def put_report(name: str, report: dict[str, Any]) -> str:
    path = iui_root() / "reports" / f"{name}.json"
    _write(path, report)
    return str(path)


def get_report(name: str) -> dict[str, Any] | None:
    return _read(iui_root() / "reports" / f"{name}.json")


def put_change_set(change_id: str, obj: dict[str, Any]) -> str:
    path = iui_root() / "changes" / f"{change_id}.json"
    _write(path, obj)
    return str(path)


def reset_store() -> None:
    global _ROOT
    root = iui_root()
    if root.exists():
        shutil.rmtree(root)
    _ROOT = None
    iui_root()
