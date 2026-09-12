"""IERE run store — retrieval traces, graphs, packs (in-memory + disk)."""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_RUNS: list[dict[str, Any]] = []
_PACKS: dict[str, dict[str, Any]] = {}
_GRAPHS: dict[str, dict[str, Any]] = {}


def reset() -> None:
    _RUNS.clear()
    _PACKS.clear()
    _GRAPHS.clear()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def store_root() -> Path:
    root = Path(
        os.environ.get(
            "IERE_STORE_ROOT",
            str(Path(__file__).resolve().parents[1] / "data" / "evidence_retrieval"),
        )
    )
    for sub in ("runs", "packs", "graphs", "reports"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def record_run(report: dict[str, Any]) -> None:
    with _LOCK:
        _RUNS.append(deepcopy(report))
        _RUNS[:] = _RUNS[-100:]
        _write(store_root() / "reports" / "last_run.json", report)
        rid = report.get("retrieval_id")
        if rid:
            _write(store_root() / "runs" / f"{rid}.json", report)


def last_run() -> dict[str, Any] | None:
    if _RUNS:
        return deepcopy(_RUNS[-1])
    path = store_root() / "reports" / "last_run.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def put_pack(pack_id: str, pack: dict[str, Any]) -> None:
    with _LOCK:
        _PACKS[pack_id] = deepcopy(pack)
        _write(store_root() / "packs" / f"{pack_id}.json", pack)


def get_pack(pack_id: str) -> dict[str, Any] | None:
    if pack_id in _PACKS:
        return deepcopy(_PACKS[pack_id])
    path = store_root() / "packs" / f"{pack_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def put_graph(graph_id: str, graph: dict[str, Any]) -> None:
    with _LOCK:
        _GRAPHS[graph_id] = deepcopy(graph)
        _write(store_root() / "graphs" / f"{graph_id}.json", graph)


def get_graph(graph_id: str) -> dict[str, Any] | None:
    if graph_id in _GRAPHS:
        return deepcopy(_GRAPHS[graph_id])
    path = store_root() / "graphs" / f"{graph_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None
