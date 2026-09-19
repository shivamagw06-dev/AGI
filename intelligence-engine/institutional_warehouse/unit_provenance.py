"""Establish the unit a source documents, for rows that only ever assumed it.

The reconciliation dry run could not rank the warehouse. It kept 55 of 68,866
annual rows and called the rest unreviewable - not because the data is wrong,
but because a row is only canonical when its units are *known*, and 47,474
Capital IQ rows carry ``sys_reported_unit='inr_million'`` with
``sys_unit_method='assumed_canonical'``.

Both facts are true at once. The unit label is right; the method says nobody
established it. ``resolve_unit`` fell through to "treat the value as already
canonical" because ``capital_iq_workbook`` was missing from SOURCE_DEFAULT_UNIT,
and that entry - added later - only governs new writes.

The distinction is worth keeping rather than papering over: *assumed* is what
stored absolute rupees in a column of INR million, and a rule that accepts an
assumption is the rule that let that happen. So this does not relax the rule. It
establishes the fact the rule is asking for, for one source whose every write
path states INR million (capiq_workbook, capiq_normalization and
capiq_background all declare it), and for no other source.

What this changes and what it does not
--------------------------------------
Changes ``sys_unit_method`` only. No financial value is read, written or
rescaled - the scale for inr_million is 1.0, so there is nothing to convert even
in principle. A stored number cannot move.

Idempotent by construction: the predicate matches only rows still marked
assumed, so a second run matches nothing.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from institutional_warehouse import audit, db, units
from institutional_warehouse.values import now_iso

#: The one source this applies to, and the exact state it must be in.
SOURCE = "capital_iq_workbook"
FROM_METHOD = units.METHOD_ASSUMED
TO_METHOD = units.METHOD_SOURCE_DEFAULT
EXPECTED_UNIT = "inr_million"

#: Tabs worth doing this for. Both hold statement money in INR million.
TABS = ("financials_annual", "financials_quarterly")

_PREDICATE = (
    'source = ? AND sys_reported_unit = ? AND sys_unit_method = ?'
)
_ARGS = (SOURCE, EXPECTED_UNIT, FROM_METHOD)


def _table(tab_id: str) -> str:
    return db.physical_table(tab_id)


def _count(tab_id: str, where: str, args: tuple) -> int:
    rows = db.query(f"SELECT COUNT(*) AS n FROM {_table(tab_id)} WHERE {where}", args)
    return int((rows[0] if rows else {}).get("n") or 0)


def plan(tab_id: str, *, sample: int = 10) -> dict[str, Any]:
    """What the backfill would do, without doing any of it.

    Returns the counts before, the rows it would touch, a sample of their ids,
    and the SQL that would undo it.
    """
    if tab_id not in TABS:
        return {"ok": False, "error": f"tab_not_eligible:{tab_id}"}

    db.init()
    table = _table(tab_id)
    eligible = _count(tab_id, _PREDICATE, _ARGS)

    ids = [str(r.get("row_id")) for r in db.query(
        f"SELECT row_id FROM {table} WHERE {_PREDICATE} LIMIT ?", _ARGS + (int(sample),))]

    # Rows this source holds that the predicate deliberately does not match, so
    # the scope of what is being left alone is visible rather than implied.
    total_for_source = _count(tab_id, "source = ?", (SOURCE,))
    other_units = db.query(
        f"SELECT sys_reported_unit AS unit, sys_unit_method AS method, COUNT(*) AS n"
        f" FROM {table} WHERE source = ? GROUP BY unit, method", (SOURCE,))

    return {
        "ok": True,
        "dry_run": True,
        "tab": tab_id,
        "source": SOURCE,
        "from_method": FROM_METHOD,
        "to_method": TO_METHOD,
        "expected_unit": EXPECTED_UNIT,
        "rows_eligible": eligible,
        "rows_for_source_total": total_for_source,
        "rows_left_alone": total_for_source - eligible,
        "source_unit_breakdown": [dict(r) for r in other_units],
        "sample_row_ids": ids,
        "forward_sql": (
            f"UPDATE {table} SET sys_unit_method = '{TO_METHOD}'"
            f" WHERE source = '{SOURCE}' AND sys_reported_unit = '{EXPECTED_UNIT}'"
            f" AND sys_unit_method = '{FROM_METHOD}';"
        ),
        # Deliberately not SQL. A rollback cannot be written before the run it
        # undoes exists, because the only safe target is the set of row ids that
        # run actually changed - see rollback_sql().
        "rollback": "available after apply(), by run_id, against the audited row ids",
        "values_touched": 0,
        "note": "sys_unit_method only; inr_million scale is 1.0 so no value can move",
    }


def plan_all(*, sample: int = 10) -> dict[str, Any]:
    plans = {tab: plan(tab, sample=sample) for tab in TABS}
    return {
        "ok": True,
        "dry_run": True,
        "total_rows_eligible": sum(p.get("rows_eligible") or 0 for p in plans.values()),
        "tabs": plans,
    }


def apply(tab_id: str, *, actor: str, confirm: bool = False) -> dict[str, Any]:
    """Perform the backfill. Refuses unless explicitly confirmed.

    Records the id of every row it changes, so the rollback can target exactly
    those rows. A predicate-shaped rollback ("set every source_default row back
    to assumed") cannot tell a row this run moved from one that was legitimately
    source_default beforehand, and would silently corrupt the second kind.
    """
    if tab_id not in TABS:
        return {"ok": False, "error": f"tab_not_eligible:{tab_id}"}
    if not confirm:
        return {"ok": False, "error": "confirm_required", "plan": plan(tab_id)}

    db.init()
    table = _table(tab_id)
    # Captured before the update, because afterwards the predicate no longer
    # matches them and there is no way back to the list.
    targets = [str(r.get("row_id")) for r in db.query(
        f"SELECT row_id FROM {table} WHERE {_PREDICATE}", _ARGS)]
    if not targets:
        return {"ok": True, "changed": 0, "already_done": True, "tab": tab_id}

    run_id = uuid.uuid4().hex
    stamp = now_iso()
    db.execute(
        "INSERT INTO wh_provenance_runs (run_id, created_at, tab_id, kind, actor,"
        " source, from_value, to_value, rows_changed, rolled_back_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,NULL)",
        (run_id, stamp, tab_id, "unit_provenance", actor, SOURCE,
         FROM_METHOD, TO_METHOD, len(targets)))
    for batch in _chunks(targets, 500):
        db.executemany(
            "INSERT INTO wh_provenance_run_rows (run_id, row_id, tab_id, column_key,"
            " old_value, new_value) VALUES (?,?,?,?,?,?)",
            [(run_id, rid, tab_id, "sys_unit_method", FROM_METHOD, TO_METHOD)
             for rid in batch])

    db.execute(
        f"UPDATE {table} SET sys_unit_method = ? WHERE {_PREDICATE}",
        (TO_METHOD,) + _ARGS)
    remaining = _count(tab_id, _PREDICATE, _ARGS)

    result = {"ok": True, "tab": tab_id, "run_id": run_id,
              "changed": len(targets), "still_assumed": remaining,
              "rollback_sql": rollback_sql(run_id)}
    audit.record("unit_provenance_backfill", tab_id=tab_id, actor=actor,
                 detail={**result, "source": SOURCE, "from": FROM_METHOD,
                         "to": TO_METHOD, "rollback_sql": "<see run_id>"},
                 ok=True)
    return result


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def runs(*, limit: int = 20) -> dict[str, Any]:
    """Every provenance run, so a rollback target can be chosen by fact."""
    db.init()
    return {"ok": True, "runs": [dict(r) for r in db.query(
        "SELECT * FROM wh_provenance_runs ORDER BY created_at DESC LIMIT ?",
        (int(limit),))]}


def rollback_sql(run_id: str, *, inline_limit: int = 200) -> str:
    """SQL that undoes exactly one run, and touches nothing else.

    Targeted by row id rather than by predicate. The rows this run moved and the
    rows that were already ``source_default`` before it are indistinguishable
    afterwards, so a predicate would revert both and quietly unstamp provenance
    that somebody had legitimately established.
    """
    db.init()
    rows = db.query(
        "SELECT row_id, tab_id, old_value FROM wh_provenance_run_rows WHERE run_id = ?",
        (run_id,))
    if not rows:
        return f"-- no recorded rows for run_id {run_id}; nothing to roll back"

    tab_id = str(rows[0].get("tab_id"))
    table = _table(tab_id)
    old = str(rows[0].get("old_value") or FROM_METHOD)
    header = (f"-- Rollback of provenance run {run_id} ({len(rows)} rows, {tab_id}).\n"
              f"-- Restores sys_unit_method only. No financial value is referenced.\n")
    if len(rows) <= inline_limit:
        ids = ", ".join(f"'{r['row_id']}'" for r in rows)
        return (header + f"UPDATE {table} SET sys_unit_method = '{old}'\n"
                f" WHERE row_id IN ({ids});")
    # Too many ids to inline: join against the audit table, which is the record
    # of what this run did and is the only correct target.
    return (header +
            f"UPDATE {table} SET sys_unit_method = (\n"
            f"    SELECT r.old_value FROM wh_provenance_run_rows r\n"
            f"     WHERE r.run_id = '{run_id}' AND r.row_id = {table}.row_id)\n"
            f" WHERE row_id IN (SELECT row_id FROM wh_provenance_run_rows\n"
            f"                   WHERE run_id = '{run_id}');")


def rollback(run_id: str, *, actor: str, confirm: bool = False) -> dict[str, Any]:
    """Undo one run against its audited row ids."""
    db.init()
    runs_found = db.query("SELECT * FROM wh_provenance_runs WHERE run_id = ?", (run_id,))
    if not runs_found:
        return {"ok": False, "error": f"unknown_run:{run_id}"}
    run = dict(runs_found[0])
    if run.get("rolled_back_at"):
        return {"ok": True, "already_rolled_back": True, "run_id": run_id}
    if not confirm:
        return {"ok": False, "error": "confirm_required",
                "run": run, "rollback_sql": rollback_sql(run_id)}

    tab_id = str(run.get("tab_id"))
    table = _table(tab_id)
    rows = db.query(
        "SELECT row_id, old_value FROM wh_provenance_run_rows WHERE run_id = ?", (run_id,))
    for batch in _chunks(rows, 500):
        db.executemany(
            f"UPDATE {table} SET sys_unit_method = ? WHERE row_id = ?",
            [(str(r.get("old_value") or FROM_METHOD), str(r.get("row_id"))) for r in batch])

    stamp = now_iso()
    db.execute("UPDATE wh_provenance_runs SET rolled_back_at = ? WHERE run_id = ?",
               (stamp, run_id))
    audit.record("unit_provenance_rollback", tab_id=tab_id, actor=actor,
                 detail={"run_id": run_id, "rows_restored": len(rows)}, ok=True)
    return {"ok": True, "run_id": run_id, "rows_restored": len(rows), "tab": tab_id}


def simulated_method(row: dict[str, Any]) -> Optional[str]:
    """The method this row would carry after the backfill, without writing it.

    Lets the inventory be re-run against the proposed state so the effect can be
    read before production is touched, using the same predicate as the real
    thing rather than a second description of it.
    """
    if (str(row.get("source") or "") == SOURCE
            and str(row.get("sys_reported_unit") or "") == EXPECTED_UNIT
            and str(row.get("sys_unit_method") or "") == FROM_METHOD):
        return TO_METHOD
    return None
