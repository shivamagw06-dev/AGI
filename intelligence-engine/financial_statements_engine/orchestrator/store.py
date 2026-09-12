"""Durable workflow store under FSE_STORE_ROOT/orchestrator/."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic

_LOCK = threading.Lock()


def orch_root() -> Path:
    root = ensure_dirs() / "orchestrator"
    for name in ("workflows", "history", "indexes"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def workflow_path(workflow_id: str) -> Path:
    safe = workflow_id.replace(":", "_")
    return orch_root() / "workflows" / f"{safe}.json"


def load_workflow(workflow_id: str) -> dict[str, Any] | None:
    path = workflow_path(workflow_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_workflow(wf: dict[str, Any]) -> Path:
    path = workflow_path(str(wf["workflow_id"]))
    with _LOCK:
        write_json_atomic(path, wf)
        _append_history(wf)
        _index_workflow(wf)
    return path


def _append_history(wf: dict[str, Any]) -> None:
    hist = orch_root() / "history" / "transitions.jsonl"
    with hist.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "workflow_id": wf.get("workflow_id"),
                    "state": wf.get("state"),
                    "current_stage": wf.get("current_stage"),
                    "ts": now_iso(),
                    "retries": wf.get("retries"),
                    "failure_reason": wf.get("failure_reason"),
                },
                sort_keys=True,
                default=str,
            )
            + "\n"
        )


def _index_workflow(wf: dict[str, Any]) -> None:
    idx = orch_root() / "indexes" / "by_state.json"
    data: dict[str, list[str]] = {}
    if idx.exists():
        try:
            data = json.loads(idx.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    wid = str(wf["workflow_id"])
    # remove from all buckets
    for key in list(data.keys()):
        data[key] = [x for x in data[key] if x != wid]
    state = str(wf.get("state") or "RECEIVED")
    data.setdefault(state, []).append(wid)
    write_json_atomic(idx, data)


def list_workflows(*, state: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    d = orch_root() / "workflows"
    rows: list[dict[str, Any]] = []
    for p in sorted(d.glob("wf_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            row = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if state and row.get("state") != state:
            continue
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def history_tail(limit: int = 100) -> list[dict[str, Any]]:
    path = orch_root() / "history" / "transitions.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-max(1, limit) :]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def count_by_state() -> dict[str, int]:
    counts: dict[str, int] = {}
    for wf in list_workflows(limit=10_000):
        st = str(wf.get("state") or "UNKNOWN")
        counts[st] = counts.get(st, 0) + 1
    return counts
