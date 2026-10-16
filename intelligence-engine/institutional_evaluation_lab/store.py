"""In-process IEL run store + baseline persistence helpers."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

_LOCK = Lock()
_RUNS: list[dict[str, Any]] = []
_MAX = 100
_BASELINE_PATH = Path(__file__).resolve().parent / "reports" / "baseline.json"


def record_run(summary: dict[str, Any]) -> dict[str, Any]:
    row = {
        "record_id": f"iel-{uuid4().hex[:12]}",
        **{k: v for k, v in summary.items() if k != "rows"},
    }
    with _LOCK:
        _RUNS.append(row)
        if len(_RUNS) > _MAX:
            del _RUNS[: len(_RUNS) - _MAX]
    return deepcopy(row)


def list_runs(*, limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        rows = list(_RUNS)
    return deepcopy(list(reversed(rows[-max(1, min(int(limit), 100)) :])))


def load_baseline() -> dict[str, Any] | None:
    if not _BASELINE_PATH.exists():
        return None
    try:
        return json.loads(_BASELINE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_baseline(summary: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "run_id": summary.get("run_id"),
        "suite": summary.get("suite"),
        "pass_pct": summary.get("aggregate", {}).get("pass_pct"),
        "mean_score": summary.get("aggregate", {}).get("mean_score"),
        "n": summary.get("aggregate", {}).get("n"),
        "iel_version": summary.get("iel_version"),
        "commit": summary.get("commit"),
        "aggregate": summary.get("aggregate"),
    }
    _BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _BASELINE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
