"""Warehouse store — reads, writes, overrides and versioning.

Write rules enforced here:

* Imported values land in the tab table and are never deleted by an edit.
* Admin edits land in the override layer; reads overlay overrides on top.
* Every changed cell is journalled and every write snapshots the row.
* Append tabs (market history, statements, consensus, ...) key on a period so a
  re-import creates a new period row instead of rewriting history.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse import audit, db, versions
from institutional_warehouse.schema import Tab, find_tab, tab as get_tab
from institutional_warehouse.values import (
    as_text,
    coerce,
    display,
    equalish,
    is_blank,
    normalise_entity,
    now_iso,
)

CHUNK = 400
MAX_LIMIT = 5000


# --------------------------------------------------------------------------
# Keys
# --------------------------------------------------------------------------


def key_values(tab: Tab, values: dict[str, Any]) -> list[str]:
    out = []
    for key in tab.key:
        column = tab.column(key)
        raw = values.get(key)
        if column is not None:
            raw = coerce(column, raw)
        text = "" if raw is None else str(raw).strip()
        if column is not None and column.type == "text":
            text = text.upper() if key in ("symbol", "company_id", "bse_symbol") else text
        out.append(text)
    return out


def make_row_id(tab: Tab, values: dict[str, Any]) -> Optional[str]:
    parts = key_values(tab, values)
    if any(p == "" for p in parts):
        return None
    digest = hashlib.sha1(("|".join([tab.id, *parts])).encode("utf-8")).hexdigest()
    return digest[:32]


def entity_of(tab: Tab, values: dict[str, Any]) -> Optional[str]:
    if not tab.entity_column:
        return None
    return normalise_entity(values.get(tab.entity_column))


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

_FILTER_OPS = {
    "eq": "= ?",
    "ne": "<> ?",
    "gt": "> ?",
    "gte": ">= ?",
    "lt": "< ?",
    "lte": "<= ?",
    "contains": "LIKE ?",
    "starts": "LIKE ?",
}


def _build_filters(tab: Tab, filters: Optional[dict[str, Any]]) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for raw_key, spec in (filters or {}).items():
        column = tab.column(str(raw_key))
        if column is None:
            continue
        op = "eq"
        value: Any = spec
        if isinstance(spec, dict):
            op = str(spec.get("op") or "eq").lower()
            value = spec.get("value")
        if op == "empty":
            clauses.append(f'("{column.key}" IS NULL OR "{column.key}" = \'\')')
            continue
        if op == "not_empty":
            clauses.append(f'("{column.key}" IS NOT NULL AND "{column.key}" <> \'\')')
            continue
        if op == "in":
            items = value if isinstance(value, (list, tuple)) else [value]
            items = [coerce(column, v) for v in items if not is_blank(v)]
            if not items:
                continue
            marks = ", ".join("?" for _ in items)
            clauses.append(f'"{column.key}" IN ({marks})')
            params.extend(items)
            continue
        if op not in _FILTER_OPS:
            op = "eq"
        if is_blank(value):
            continue
        if op in ("contains", "starts"):
            text = str(value).strip()
            clauses.append(f'LOWER(CAST("{column.key}" AS TEXT)) LIKE ?')
            params.append(f"{text.lower()}%" if op == "starts" else f"%{text.lower()}%")
            continue
        clauses.append(f'"{column.key}" {_FILTER_OPS[op]}')
        params.append(coerce(column, value))
    return clauses, params


def _build_search(tab: Tab, search: Optional[str]) -> tuple[list[str], list[Any]]:
    text = (search or "").strip().lower()
    if not text:
        return [], []
    cols = list(tab.search_columns) or [c.key for c in tab.columns if c.type == "text"][:6]
    if not cols:
        return [], []
    ors = [f'LOWER(CAST("{c}" AS TEXT)) LIKE ?' for c in cols if tab.column(c)]
    if not ors:
        return [], []
    return [f"({' OR '.join(ors)})"], [f"%{text}%"] * len(ors)


def _build_order(tab: Tab, sort: Optional[str], order: str) -> str:
    direction = "DESC" if str(order or "").lower() == "desc" else "ASC"
    if sort:
        column = tab.column(str(sort))
        if column is not None:
            return f'"{column.key}" {direction}'
    parts = []
    for spec in (tab.order_by or tab.key):
        raw = spec.strip()
        desc = raw.upper().endswith(" DESC")
        name = raw.split(" ")[0]
        if tab.column(name) is None:
            continue
        parts.append(f'"{name}" {"DESC" if desc else "ASC"}')
    return ", ".join(parts) if parts else "row_id ASC"


def _overrides_for(tab_id: str, row_ids: Sequence[str]) -> dict[str, dict[str, dict[str, Any]]]:
    if not row_ids:
        return {}
    out: dict[str, dict[str, dict[str, Any]]] = {}
    ids = list(row_ids)
    for start in range(0, len(ids), CHUNK):
        batch = ids[start:start + CHUNK]
        marks = ", ".join("?" for _ in batch)
        rows = db.query(
            f"SELECT row_id, column_key, value, actor, reason, created_at FROM wh_overrides"
            f" WHERE tab_id = ? AND active = 1 AND row_id IN ({marks})",
            (tab_id, *batch),
        )
        for row in rows:
            out.setdefault(str(row["row_id"]), {})[str(row["column_key"])] = {
                "value": row.get("value"),
                "actor": row.get("actor"),
                "reason": row.get("reason"),
                "at": row.get("created_at"),
            }
    return out


def _shape_row(tab: Tab, raw: dict[str, Any], overrides: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row: dict[str, Any] = {"row_id": raw.get("row_id")}
    for column in tab.columns:
        row[column.key] = display(column, raw.get(column.key))
    overridden = []
    for column_key, meta in (overrides or {}).items():
        column = tab.column(column_key)
        if column is None:
            continue
        row[column_key] = display(column, coerce(column, meta.get("value")))
        overridden.append(column_key)
    row["_meta"] = {
        "version": int(raw.get("sys_version") or 1),
        "created_at": raw.get("sys_created_at"),
        "updated_at": raw.get("sys_updated_at"),
        "published": bool(raw.get("sys_published")),
        "import_id": raw.get("sys_import_id"),
        "entity": raw.get("sys_entity"),
        # What the vendor reported in, and how the row reached INR million. A
        # null reported_unit means the row predates unit normalisation.
        "reported_unit": raw.get("sys_reported_unit"),
        "unit_scale": raw.get("sys_unit_scale"),
        "unit_method": raw.get("sys_unit_method"),
        "overridden": sorted(overridden),
        "override_detail": {k: overrides[k] for k in overridden} if overridden else {},
    }
    return row


def fetch(
    tab_id: str,
    *,
    entity: Optional[str] = None,
    filters: Optional[dict[str, Any]] = None,
    search: Optional[str] = None,
    sort: Optional[str] = None,
    order: str = "asc",
    limit: int = 200,
    offset: int = 0,
    include_overrides: bool = True,
) -> dict[str, Any]:
    tab = get_tab(tab_id)
    table = db.physical_table(tab.id)
    clauses, params = _build_filters(tab, filters)
    # Retired rows remain in the append-only audit ledger but must never feed
    # products or the normal warehouse grid.
    clauses.append("COALESCE(sys_published, 1) = 1")
    s_clauses, s_params = _build_search(tab, search)
    clauses += s_clauses
    params += s_params
    if entity and tab.entity_column:
        clauses.append("sys_entity = ?")
        params.append(normalise_entity(entity))
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    total = db.count(table, " AND ".join(clauses), params)
    limit = max(1, min(int(limit or 200), MAX_LIMIT))
    offset = max(0, int(offset or 0))
    raw_rows = db.query(
        f"SELECT * FROM {table}{where} ORDER BY {_build_order(tab, sort, order)} LIMIT ? OFFSET ?",
        (*params, limit, offset),
    )
    overrides = _overrides_for(tab.id, [str(r.get("row_id")) for r in raw_rows]) if include_overrides else {}
    rows = [_shape_row(tab, r, overrides.get(str(r.get("row_id")), {})) for r in raw_rows]
    return {
        "ok": True,
        "tab": tab.id,
        "label": tab.label,
        "total": total,
        "limit": limit,
        "offset": offset,
        "returned": len(rows),
        "rows": rows,
    }


def get(tab_id: str, row_id: str) -> Optional[dict[str, Any]]:
    tab = get_tab(tab_id)
    rows = db.query(
        f"SELECT * FROM {db.physical_table(tab.id)} WHERE row_id = ? AND COALESCE(sys_published, 1) = 1",
        (row_id,),
    )
    if not rows:
        return None
    overrides = _overrides_for(tab.id, [row_id])
    return _shape_row(tab, rows[0], overrides.get(row_id, {}))


def raw_row(tab_id: str, row_id: str) -> Optional[dict[str, Any]]:
    tab = get_tab(tab_id)
    rows = db.query(f"SELECT * FROM {db.physical_table(tab.id)} WHERE row_id = ?", (row_id,))
    return rows[0] if rows else None


def all_rows(tab_id: str, *, entity: Optional[str] = None, limit: int = MAX_LIMIT) -> list[dict[str, Any]]:
    """Effective rows (overrides applied) for engine consumers.

    ``fetch`` clamps each page to ``MAX_LIMIT`` (5000). Callers that need a
    fuller tab scan — coverage audits, EMPTY fill queues — pass a higher
    ``limit``; we page internally so they are not silently truncated.
    """
    want = max(1, int(limit or MAX_LIMIT))
    if want <= MAX_LIMIT:
        return list(fetch(tab_id, entity=entity, limit=want).get("rows") or [])

    out: list[dict[str, Any]] = []
    offset = 0
    while len(out) < want:
        page_limit = min(MAX_LIMIT, want - len(out))
        page = fetch(tab_id, entity=entity, limit=page_limit, offset=offset)
        rows = list(page.get("rows") or [])
        if not rows:
            break
        out.extend(rows)
        offset += len(rows)
        total = int(page.get("total") or 0)
        if offset >= total or len(rows) < page_limit:
            break
    return out[:want]


def entities(tab_id: str) -> list[str]:
    tab = get_tab(tab_id)
    if not tab.entity_column:
        return []
    rows = db.query(
        f"SELECT DISTINCT sys_entity FROM {db.physical_table(tab.id)}"
        " WHERE sys_entity IS NOT NULL ORDER BY sys_entity"
    )
    return [str(r["sys_entity"]) for r in rows if r.get("sys_entity")]


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------


def upsert(
    tab_id: str,
    rows: Iterable[dict[str, Any]],
    *,
    source: str,
    actor: str = "system",
    import_id: Optional[str] = None,
    reason: Optional[str] = None,
    journal: bool = True,
    published: bool = True,
    fill_only: bool = False,
) -> dict[str, Any]:
    """Insert or update rows keyed by the tab's natural key.

    Returns counts plus the row ids touched. Unchanged rows are left alone so a
    daily refresh does not inflate the version history.

    ``fill_only`` makes a source a gap-filler: it may create a row that is not
    there, and may never change one that is. Some feeds carry data no other feed
    has - the NSE bhavcopy is the only place a delisted company still exists -
    while being the wrong authority for a row somebody else already wrote.
    """
    tab = get_tab(tab_id)
    table = db.physical_table(tab.id)
    db.init()

    prepared: list[dict[str, Any]] = []
    skipped = 0
    for incoming in rows:
        if not isinstance(incoming, dict):
            skipped += 1
            continue
        row_id = make_row_id(tab, incoming)
        if not row_id:
            skipped += 1
            continue
        values: dict[str, Any] = {}
        for column in tab.columns:
            if column.key not in incoming:
                continue
            values[column.key] = coerce(column, incoming.get(column.key))
        if not values:
            skipped += 1
            continue
        prepared.append({"row_id": row_id, "values": values, "entity": entity_of(tab, incoming)})

    # A single batch can carry the same natural key twice (two shareholding
    # records for one quarter, two feeds for one trading day). Merge them so the
    # last value wins instead of colliding on the primary key.
    if prepared:
        merged: dict[str, dict[str, Any]] = {}
        for item in prepared:
            seen = merged.get(item["row_id"])
            if seen is None:
                merged[item["row_id"]] = item
            else:
                seen["values"].update({k: v for k, v in item["values"].items() if v is not None})
                seen["entity"] = item["entity"] or seen["entity"]
        collapsed = len(prepared) - len(merged)
        prepared = list(merged.values())
    else:
        collapsed = 0

    if not prepared:
        return {"ok": True, "tab": tab.id, "inserted": 0, "updated": 0, "unchanged": 0, "skipped": skipped}

    existing: dict[str, dict[str, Any]] = {}
    ids = [p["row_id"] for p in prepared]
    for start in range(0, len(ids), CHUNK):
        batch = ids[start:start + CHUNK]
        marks = ", ".join("?" for _ in batch)
        for row in db.query(f"SELECT * FROM {table} WHERE row_id IN ({marks})", batch):
            existing[str(row["row_id"])] = row

    # A failed refresh must not erase a value that is already there.
    #
    # A vendor having a bad morning returns nulls, and writing them turns a
    # working figure on the desk into a blank with no explanation. The stored
    # value stays and its freshness is what changes.
    nulled = 0
    if existing:
        from institutional_warehouse import ownership

        cleaned: list[dict[str, Any]] = []
        for item in prepared:
            prior = existing.get(item["row_id"])
            if not prior:
                cleaned.append(item)
                continue
            values = item["values"]
            for field in [k for k, v in values.items() if v is None]:
                if prior.get(field) is not None:
                    values.pop(field, None)
                    nulled += 1
            cleaned.append(item)
        prepared = [p for p in cleaned if p["values"]]

    # A gap-filler only fills gaps. The bhavcopy walker collected days that
    # Upstox had already written, and because both land in `close` it replaced
    # split-adjusted prices with the raw price that traded on the day. For
    # Dr. Lal PathLabs that turned a +12% year into a published -45%.
    left_alone = 0
    if fill_only:
        before = len(prepared)
        prepared = [p for p in prepared if p["row_id"] not in existing]
        left_alone = before - len(prepared)
        if not prepared:
            return {"ok": True, "tab": tab.id, "inserted": 0, "updated": 0,
                    "unchanged": 0, "skipped": skipped, "left_alone": left_alone,
                    "nulls_refused": nulled}

    stamp = now_iso()
    inserted = updated = unchanged = 0
    cell_entries: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    insert_payload: list[tuple[Any, ...]] = []
    column_keys = [c.key for c in tab.columns]

    for item in prepared:
        row_id = item["row_id"]
        values = item["values"]
        entity = item["entity"]
        current = existing.get(row_id)
        if "source" in column_keys:
            values.setdefault("source", source)
        if "last_updated" in column_keys:
            values["last_updated"] = stamp
        if "import_time" in column_keys and current is None:
            values.setdefault("import_time", stamp)

        if current is None:
            version = 1
            payload = {k: values.get(k) for k in column_keys}
            insert_payload.append(
                (
                    row_id,
                    *[payload.get(k) for k in column_keys],
                    version,
                    stamp,
                    stamp,
                    1 if published else 0,
                    import_id,
                    entity,
                )
            )
            inserted += 1
            if journal:
                snapshots.append(
                    {
                        "tab_id": tab.id,
                        "row_id": row_id,
                        "entity": entity,
                        "version": version,
                        "payload": payload,
                        "actor": actor,
                        "reason": reason or f"import:{source}",
                        "kind": "insert",
                    }
                )
            continue

        changes = {}
        for key, value in values.items():
            if key in ("last_updated", "import_time"):
                continue
            if not equalish(current.get(key), value):
                changes[key] = value
        if not changes:
            unchanged += 1
            continue

        version = int(current.get("sys_version") or 1) + 1
        assignments = ", ".join(f'"{k}" = ?' for k in values)
        db.execute(
            f"UPDATE {table} SET {assignments}, sys_version = ?, sys_updated_at = ?,"
            " sys_import_id = ?, sys_entity = ? WHERE row_id = ?",
            (*values.values(), version, stamp, import_id, entity or current.get("sys_entity"), row_id),
        )
        updated += 1
        if journal:
            for key, value in changes.items():
                cell_entries.append(
                    {
                        "tab_id": tab.id,
                        "row_id": row_id,
                        "entity": entity,
                        "column": key,
                        "old_value": current.get(key),
                        "new_value": value,
                        "actor": actor,
                        "reason": reason or f"import:{source}",
                        "source": source,
                        "version": version,
                    }
                )
            merged = {k: current.get(k) for k in column_keys}
            merged.update(values)
            snapshots.append(
                {
                    "tab_id": tab.id,
                    "row_id": row_id,
                    "entity": entity,
                    "version": version,
                    "payload": merged,
                    "actor": actor,
                    "reason": reason or f"import:{source}",
                    "kind": "update",
                }
            )

    if insert_payload:
        cols = ", ".join(f'"{k}"' for k in column_keys)
        marks = ", ".join("?" for _ in range(len(column_keys) + 7))
        db.executemany(
            f"INSERT INTO {table} (row_id, {cols}, sys_version, sys_created_at, sys_updated_at,"
            f" sys_published, sys_import_id, sys_entity) VALUES ({marks})",
            insert_payload,
        )
    if cell_entries:
        versions.record_cell_changes(cell_entries)
    if snapshots:
        versions.snapshot_rows(snapshots)

    return {
        "ok": True,
        "tab": tab.id,
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "collapsed": collapsed,
        "left_alone": left_alone,
        # Values a failed refresh tried to blank and was refused. Reported
        # because a silent refusal looks identical to nothing having happened.
        "nulls_refused": nulled,
        "source": source,
        "at": stamp,
    }


def create_row(tab_id: str, values: dict[str, Any], *, actor: str, source: str = "manual") -> dict[str, Any]:
    tab = get_tab(tab_id)
    if tab.read_only:
        return {"ok": False, "error": f"tab_read_only:{tab.id}"}
    missing = [k for k in tab.key if is_blank(values.get(k))]
    if missing:
        return {"ok": False, "error": "missing_key", "columns": missing}
    result = upsert(tab.id, [values], source=source, actor=actor, reason="manual_create")
    row_id = make_row_id(tab, values)
    audit.record("create", tab_id=tab.id, row_id=row_id or "", entity=entity_of(tab, values),
                 actor=actor, detail={"values": values})
    return {**result, "row_id": row_id, "row": get(tab.id, row_id) if row_id else None}


def set_cells(
    tab_id: str,
    edits: Sequence[dict[str, Any]],
    *,
    actor: str,
    reason: Optional[str] = None,
) -> dict[str, Any]:
    """Apply admin edits as overrides. Imported values are never destroyed."""
    tab = get_tab(tab_id)
    if tab.read_only:
        return {"ok": False, "error": f"tab_read_only:{tab.id}", "applied": 0}

    applied = 0
    rejected: list[dict[str, Any]] = []
    touched: set[str] = set()
    stamp = now_iso()

    for edit in edits:
        row_id = str(edit.get("row_id") or "").strip()
        column_key = str(edit.get("column") or "").strip()
        column = tab.column(column_key)
        if not row_id or column is None:
            rejected.append({"row_id": row_id, "column": column_key, "error": "unknown_column"})
            continue
        if column.computed or not column.editable:
            rejected.append({"row_id": row_id, "column": column_key, "error": "column_not_editable"})
            continue
        current_raw = raw_row(tab.id, row_id)
        if current_raw is None:
            rejected.append({"row_id": row_id, "column": column_key, "error": "row_not_found"})
            continue
        new_value = coerce(column, edit.get("value"))
        base_value = current_raw.get(column_key)
        existing_override = db.query(
            "SELECT value FROM wh_overrides WHERE tab_id = ? AND row_id = ? AND column_key = ?"
            " AND active = 1 ORDER BY created_at DESC LIMIT 1",
            (tab.id, row_id, column_key),
        )
        old_effective = coerce(column, existing_override[0]["value"]) if existing_override else base_value
        if equalish(old_effective, new_value):
            continue

        db.execute(
            "UPDATE wh_overrides SET active = 0 WHERE tab_id = ? AND row_id = ? AND column_key = ? AND active = 1",
            (tab.id, row_id, column_key),
        )
        entity = current_raw.get("sys_entity")
        if new_value is None and base_value is None:
            pass  # clearing back to an empty base value: override row stays retired
        else:
            db.execute(
                "INSERT INTO wh_overrides (id, created_at, tab_id, row_id, entity, column_key, value,"
                " actor, reason, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (uuid.uuid4().hex, stamp, tab.id, row_id, entity, column_key,
                 as_text(new_value), actor, reason),
            )
        version = int(current_raw.get("sys_version") or 1) + 1
        db.execute(
            f"UPDATE {db.physical_table(tab.id)} SET sys_version = ?, sys_updated_at = ? WHERE row_id = ?",
            (version, stamp, row_id),
        )
        versions.record_cell_change(
            tab_id=tab.id,
            row_id=row_id,
            entity=entity,
            column=column_key,
            old_value=old_effective,
            new_value=new_value,
            actor=actor,
            reason=reason,
            source="admin_override",
            version=version,
        )
        applied += 1
        touched.add(row_id)

    for row_id in touched:
        current = get(tab.id, row_id)
        if current:
            versions.snapshot_row(
                tab_id=tab.id,
                row_id=row_id,
                entity=current.get("_meta", {}).get("entity"),
                version=current.get("_meta", {}).get("version", 1),
                payload={k: v for k, v in current.items() if k != "_meta"},
                actor=actor,
                reason=reason,
                kind="override",
            )

    audit.record(
        "bulk_edit" if applied > 1 else "edit",
        tab_id=tab.id,
        actor=actor,
        detail={"applied": applied, "rejected": rejected, "reason": reason},
        ok=not rejected,
    )
    return {
        "ok": True,
        "tab": tab.id,
        "applied": applied,
        "rejected": rejected,
        "rows": [get(tab.id, r) for r in sorted(touched)],
    }


def clear_override(tab_id: str, row_id: str, column: str, *, actor: str) -> dict[str, Any]:
    tab = get_tab(tab_id)
    changed = db.execute(
        "UPDATE wh_overrides SET active = 0 WHERE tab_id = ? AND row_id = ? AND column_key = ? AND active = 1",
        (tab.id, row_id, column),
    )
    audit.record("override_clear", tab_id=tab.id, row_id=row_id, actor=actor,
                 detail={"column": column, "cleared": changed})
    return {"ok": True, "cleared": changed, "row": get(tab.id, row_id)}


def restore(tab_id: str, row_id: str, *, snapshot_id: Optional[str] = None,
            version: Optional[int] = None, actor: str) -> dict[str, Any]:
    tab = get_tab(tab_id)
    snapshot = None
    if snapshot_id:
        snapshot = versions.get_snapshot(snapshot_id)
    elif version is not None:
        for snap in versions.row_snapshots(tab.id, row_id, limit=200):
            if int(snap.get("version") or 0) == int(version):
                snapshot = {**snap, "tab_id": tab.id, "row_id": row_id}
                break
    if not snapshot:
        return {"ok": False, "error": "snapshot_not_found"}

    payload = {k: v for k, v in (snapshot.get("payload") or {}).items() if tab.column(k)}
    for key in tab.key:
        payload.setdefault(key, (get(tab.id, row_id) or {}).get(key))
    # A restore is an override-layer action: the imported base is untouched.
    edits = [{"row_id": row_id, "column": k, "value": v} for k, v in payload.items()
             if tab.column(k) and tab.column(k).editable and not tab.column(k).computed]
    result = set_cells(tab.id, edits, actor=actor, reason=f"restore:{snapshot.get('version')}")
    audit.record("restore", tab_id=tab.id, row_id=row_id, actor=actor,
                 detail={"version": snapshot.get("version"), "snapshot": snapshot.get("id")})
    return {"ok": True, "restored_version": snapshot.get("version"), **result}


def delete_rows(tab_id: str, row_ids: Sequence[str], *, actor: str, reason: Optional[str] = None) -> dict[str, Any]:
    """Remove rows. Only allowed on non-append tabs; snapshots are kept forever."""
    tab = get_tab(tab_id)
    if tab.append_only:
        return {"ok": False, "error": f"append_only_tab:{tab.id}"}
    if tab.read_only:
        return {"ok": False, "error": f"tab_read_only:{tab.id}"}
    removed = 0
    for row_id in row_ids:
        current = raw_row(tab.id, row_id)
        if not current:
            continue
        versions.snapshot_row(
            tab_id=tab.id,
            row_id=row_id,
            entity=current.get("sys_entity"),
            version=int(current.get("sys_version") or 1),
            payload={k: v for k, v in current.items() if not k.startswith("sys_")},
            actor=actor,
            reason=reason,
            kind="delete",
        )
        db.execute(f"DELETE FROM {db.physical_table(tab.id)} WHERE row_id = ?", (row_id,))
        db.execute("UPDATE wh_overrides SET active = 0 WHERE tab_id = ? AND row_id = ?", (tab.id, row_id))
        removed += 1
    audit.record("delete", tab_id=tab.id, actor=actor, detail={"rows": list(row_ids), "reason": reason})
    return {"ok": True, "removed": removed}


def retire_rows(tab_id: str, row_ids: Sequence[str], *, actor: str, reason: str) -> dict[str, Any]:
    """Hide bad imported rows from active reads while retaining full audit history."""
    tab = get_tab(tab_id)
    retired = 0
    for row_id in row_ids:
        current = raw_row(tab.id, row_id)
        if not current or not current.get("sys_published"):
            continue
        versions.snapshot_row(
            tab_id=tab.id,
            row_id=row_id,
            entity=current.get("sys_entity"),
            version=int(current.get("sys_version") or 1),
            payload={k: v for k, v in current.items() if not k.startswith("sys_")},
            actor=actor,
            reason=reason,
            kind="retire",
        )
        db.execute(f"UPDATE {db.physical_table(tab.id)} SET sys_published = 0 WHERE row_id = ?", (row_id,))
        retired += 1
    audit.record("retire", tab_id=tab.id, actor=actor, detail={"rows": list(row_ids), "reason": reason})
    return {"ok": True, "retired": retired}


def publish(tab_id: str, *, actor: str, row_ids: Optional[Sequence[str]] = None) -> dict[str, Any]:
    tab = get_tab(tab_id)
    table = db.physical_table(tab.id)
    if row_ids:
        count = 0
        for row_id in row_ids:
            count += db.execute(f"UPDATE {table} SET sys_published = 1 WHERE row_id = ?", (row_id,))
    else:
        count = db.execute(f"UPDATE {table} SET sys_published = 1 WHERE sys_published IS NULL OR sys_published = 0")
    audit.record("publish", tab_id=tab.id, actor=actor, detail={"rows": count})
    return {"ok": True, "published": count}


def row_count(tab_id: str) -> int:
    return db.count(db.physical_table(get_tab(tab_id).id))


def tab_stats(tab_id: str) -> dict[str, Any]:
    tab = get_tab(tab_id)
    table = db.physical_table(tab.id)
    rows = db.count(table)
    companies = 0
    if tab.entity_column:
        res = db.query(f"SELECT COUNT(DISTINCT sys_entity) AS n FROM {table} WHERE sys_entity IS NOT NULL")
        companies = int(res[0].get("n") or 0) if res else 0
    last = db.query(f"SELECT MAX(sys_updated_at) AS t FROM {table}")
    return {
        "tab": tab.id,
        "label": tab.label,
        "rows": rows,
        "companies": companies,
        "last_updated": (last[0].get("t") if last else None),
    }


def exists(tab_id: str) -> bool:
    return find_tab(tab_id) is not None
