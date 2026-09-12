"""IDQ-only append-friendly store. Never writes into Phase 1–7 or KF stores."""

from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any

from decision_quality.schema import IDQ_VERSION

_LOCK = threading.Lock()
_DEFAULT = Path(
    os.environ.get(
        "IDQ_STORE_ROOT",
        str(Path(__file__).resolve().parents[1] / "data" / "decision_quality"),
    )
)


def idq_root() -> Path:
    root = Path(_DEFAULT)
    for sub in (
        "decisions",
        "scorecards",
        "calibration",
        "hall",
        "replays",
        "reports",
    ):
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


def put_decision(decision_id: str, obj: dict[str, Any]) -> str:
    path = idq_root() / "decisions" / f"{decision_id}.json"
    with _LOCK:
        _write(path, {**obj, "idq_version": IDQ_VERSION})
    return str(path)


def get_decision(decision_id: str) -> dict[str, Any] | None:
    return _read(idq_root() / "decisions" / f"{decision_id}.json")


def list_decisions() -> list[str]:
    return sorted(p.stem for p in (idq_root() / "decisions").glob("*.json"))


def all_decisions() -> list[dict[str, Any]]:
    out = []
    for did in list_decisions():
        obj = get_decision(did)
        if obj:
            out.append(obj)
    return out


def put_scorecard(kind: str, name: str, payload: dict[str, Any]) -> str:
    path = idq_root() / "scorecards" / kind / f"{name}.json"
    with _LOCK:
        _write(path, {**payload, "idq_version": IDQ_VERSION})
    return str(path)


def get_scorecard(kind: str, name: str) -> dict[str, Any] | None:
    return _read(idq_root() / "scorecards" / kind / f"{name}.json")


def list_scorecards(kind: str) -> list[str]:
    root = idq_root() / "scorecards" / kind
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.json"))


def put_calibration(name: str, payload: dict[str, Any]) -> str:
    path = idq_root() / "calibration" / f"{name}.json"
    with _LOCK:
        _write(path, {**payload, "idq_version": IDQ_VERSION})
    return str(path)


def get_calibration(name: str) -> dict[str, Any] | None:
    return _read(idq_root() / "calibration" / f"{name}.json")


def put_hall(payload: dict[str, Any]) -> str:
    path = idq_root() / "hall" / "INDEX.json"
    with _LOCK:
        _write(path, {**payload, "idq_version": IDQ_VERSION})
    return str(path)


def get_hall() -> dict[str, Any] | None:
    return _read(idq_root() / "hall" / "INDEX.json")


def put_replay(decision_id: str, payload: dict[str, Any]) -> str:
    path = idq_root() / "replays" / f"{decision_id}.json"
    with _LOCK:
        _write(path, {**payload, "idq_version": IDQ_VERSION})
    return str(path)


def get_replay(decision_id: str) -> dict[str, Any] | None:
    return _read(idq_root() / "replays" / f"{decision_id}.json")


def put_report(name: str, payload: dict[str, Any]) -> str:
    path = idq_root() / "reports" / f"{name}.json"
    with _LOCK:
        _write(path, {**payload, "idq_version": IDQ_VERSION})
    return str(path)


def get_report(name: str) -> dict[str, Any] | None:
    return _read(idq_root() / "reports" / f"{name}.json")


def reset_store() -> None:
    root = idq_root()
    with _LOCK:
        if root.exists():
            shutil.rmtree(root)
        idq_root()
