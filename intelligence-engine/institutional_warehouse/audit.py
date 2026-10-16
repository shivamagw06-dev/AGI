"""Audit trail — every warehouse action is written here before it is answered.

Actions: import, edit, bulk_edit, create, override_clear, publish, refresh,
recalculate, restore, validate, export.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from institutional_warehouse import db
from institutional_warehouse.values import now_iso

ACTIONS = (
    "import",
    "edit",
    "bulk_edit",
    "create",
    "delete",
    "override_clear",
    "publish",
    "refresh",
    "recalculate",
    "restore",
    "validate",
    "export",
)


def record(
    action: str,
    *,
    tab_id: str = "",
    row_id: str = "",
    entity: Optional[str] = None,
    actor: str = "system",
    detail: Any = None,
    ok: bool = True,
) -> str:
    audit_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO wh_audit (id, created_at, action, tab_id, row_id, entity, actor, detail, ok)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            audit_id,
            now_iso(),
            str(action),
            str(tab_id or ""),
            str(row_id or ""),
            (entity or None),
            str(actor or "system"),
            json.dumps(detail, default=str) if detail is not None else None,
            1 if ok else 0,
        ),
    )
    return audit_id


def recent(
    *,
    tab_id: Optional[str] = None,
    entity: Optional[str] = None,
    action: Optional[str] = None,
    actor: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if tab_id:
        clauses.append("tab_id = ?")
        params.append(tab_id)
    if entity:
        clauses.append("entity = ?")
        params.append(str(entity).upper())
    if action:
        clauses.append("action = ?")
        params.append(action)
    if actor:
        clauses.append("actor = ?")
        params.append(actor)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    total = db.count("wh_audit", " AND ".join(clauses), params)
    rows = db.query(
        f"SELECT * FROM wh_audit{where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        (*params, max(1, min(int(limit), 1000)), max(0, int(offset))),
    )
    out = []
    for row in rows:
        detail = row.get("detail")
        if detail:
            try:
                detail = json.loads(detail)
            except Exception:
                pass
        out.append(
            {
                "id": row.get("id"),
                "created_at": row.get("created_at"),
                "action": row.get("action"),
                "tab_id": row.get("tab_id"),
                "row_id": row.get("row_id"),
                "entity": row.get("entity"),
                "actor": row.get("actor"),
                "ok": bool(row.get("ok")),
                "detail": detail,
            }
        )
    return {"ok": True, "total": total, "limit": limit, "offset": offset, "entries": out}


def summary(limit: int = 12) -> dict[str, Any]:
    rows = db.query(
        "SELECT action, COUNT(*) AS n FROM wh_audit GROUP BY action ORDER BY n DESC LIMIT ?",
        (max(1, int(limit)),),
    )
    last = db.query("SELECT created_at, action, actor, tab_id FROM wh_audit ORDER BY created_at DESC LIMIT 1")
    return {
        "ok": True,
        "total": db.count("wh_audit"),
        "by_action": {str(r.get("action")): int(r.get("n") or 0) for r in rows},
        "last": last[0] if last else None,
    }
