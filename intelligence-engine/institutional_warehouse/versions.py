"""Version history — cell-level change log plus full row snapshots.

Every write to the warehouse leaves two traces:

* ``wh_cell_versions`` — one entry per changed cell (old value, new value, who,
  why, which source, which version).
* ``wh_row_snapshots`` — the complete row payload at that version, so any row
  can be diffed against, or restored to, an earlier state.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Iterable, Optional

from institutional_warehouse import db
from institutional_warehouse.values import as_text, now_iso


def record_cell_change(
    *,
    tab_id: str,
    row_id: str,
    entity: Optional[str],
    column: str,
    old_value: Any,
    new_value: Any,
    actor: str,
    reason: Optional[str],
    source: Optional[str],
    version: int,
) -> None:
    db.execute(
        "INSERT INTO wh_cell_versions (id, created_at, tab_id, row_id, entity, column_key,"
        " old_value, new_value, actor, reason, source, version)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            uuid.uuid4().hex,
            now_iso(),
            tab_id,
            row_id,
            entity,
            column,
            as_text(old_value),
            as_text(new_value),
            actor,
            reason,
            source,
            int(version),
        ),
    )


def record_cell_changes(entries: Iterable[dict[str, Any]]) -> int:
    payload = []
    stamp = now_iso()
    for entry in entries:
        payload.append(
            (
                uuid.uuid4().hex,
                stamp,
                entry["tab_id"],
                entry["row_id"],
                entry.get("entity"),
                entry["column"],
                as_text(entry.get("old_value")),
                as_text(entry.get("new_value")),
                entry.get("actor", "system"),
                entry.get("reason"),
                entry.get("source"),
                int(entry.get("version") or 1),
            )
        )
    if not payload:
        return 0
    db.executemany(
        "INSERT INTO wh_cell_versions (id, created_at, tab_id, row_id, entity, column_key,"
        " old_value, new_value, actor, reason, source, version)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    return len(payload)


def snapshot_row(
    *,
    tab_id: str,
    row_id: str,
    entity: Optional[str],
    version: int,
    payload: dict[str, Any],
    actor: str = "system",
    reason: Optional[str] = None,
    kind: str = "write",
) -> str:
    snap_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO wh_row_snapshots (id, created_at, tab_id, row_id, entity, version, payload,"
        " actor, reason, kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            snap_id,
            now_iso(),
            tab_id,
            row_id,
            entity,
            int(version),
            json.dumps(payload, default=str),
            actor,
            reason,
            kind,
        ),
    )
    return snap_id


def snapshot_rows(entries: Iterable[dict[str, Any]]) -> int:
    stamp = now_iso()
    payload = [
        (
            uuid.uuid4().hex,
            stamp,
            e["tab_id"],
            e["row_id"],
            e.get("entity"),
            int(e.get("version") or 1),
            json.dumps(e.get("payload") or {}, default=str),
            e.get("actor", "system"),
            e.get("reason"),
            e.get("kind", "write"),
        )
        for e in entries
    ]
    if not payload:
        return 0
    db.executemany(
        "INSERT INTO wh_row_snapshots (id, created_at, tab_id, row_id, entity, version, payload,"
        " actor, reason, kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    return len(payload)


def cell_history(tab_id: str, row_id: str, *, column: Optional[str] = None, limit: int = 200) -> list[dict[str, Any]]:
    clauses = ["tab_id = ?", "row_id = ?"]
    params: list[Any] = [tab_id, row_id]
    if column:
        clauses.append("column_key = ?")
        params.append(column)
    rows = db.query(
        f"SELECT * FROM wh_cell_versions WHERE {' AND '.join(clauses)}"
        " ORDER BY created_at DESC, id DESC LIMIT ?",
        (*params, max(1, min(int(limit), 1000))),
    )
    return [
        {
            "id": r.get("id"),
            "at": r.get("created_at"),
            "column": r.get("column_key"),
            "old_value": r.get("old_value"),
            "new_value": r.get("new_value"),
            "actor": r.get("actor"),
            "reason": r.get("reason"),
            "source": r.get("source"),
            "version": r.get("version"),
        }
        for r in rows
    ]


def row_snapshots(tab_id: str, row_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    rows = db.query(
        "SELECT id, created_at, version, actor, reason, kind, payload FROM wh_row_snapshots"
        " WHERE tab_id = ? AND row_id = ? ORDER BY version DESC, created_at DESC LIMIT ?",
        (tab_id, row_id, max(1, min(int(limit), 500))),
    )
    out = []
    for r in rows:
        try:
            payload = json.loads(r.get("payload") or "{}")
        except Exception:
            payload = {}
        out.append(
            {
                "id": r.get("id"),
                "at": r.get("created_at"),
                "version": r.get("version"),
                "actor": r.get("actor"),
                "reason": r.get("reason"),
                "kind": r.get("kind"),
                "payload": payload,
            }
        )
    return out


def get_snapshot(snapshot_id: str) -> Optional[dict[str, Any]]:
    rows = db.query("SELECT * FROM wh_row_snapshots WHERE id = ?", (snapshot_id,))
    if not rows:
        return None
    row = rows[0]
    try:
        payload = json.loads(row.get("payload") or "{}")
    except Exception:
        payload = {}
    return {
        "id": row.get("id"),
        "tab_id": row.get("tab_id"),
        "row_id": row.get("row_id"),
        "entity": row.get("entity"),
        "version": row.get("version"),
        "at": row.get("created_at"),
        "actor": row.get("actor"),
        "reason": row.get("reason"),
        "kind": row.get("kind"),
        "payload": payload,
    }


def diff(before: dict[str, Any], after: dict[str, Any], *, keys: Optional[Iterable[str]] = None) -> list[dict[str, Any]]:
    columns = list(keys) if keys else sorted(set(before) | set(after))
    changes = []
    for key in columns:
        if key.startswith("sys_") or key in ("row_id", "overridden"):
            continue
        old = before.get(key)
        new = after.get(key)
        if as_text(old) != as_text(new):
            changes.append({"column": key, "old_value": old, "new_value": new})
    return changes


def latest_version(tab_id: str, row_id: str) -> int:
    rows = db.query(
        "SELECT MAX(version) AS v FROM wh_row_snapshots WHERE tab_id = ? AND row_id = ?",
        (tab_id, row_id),
    )
    if not rows or rows[0].get("v") is None:
        return 0
    return int(rows[0]["v"])
