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

from typing import Any, Optional

from institutional_warehouse import audit, db, units

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
        "rollback_sql": (
            f"-- Undo: only rows this backfill moved, identified by the state it left.\n"
            f"UPDATE {table} SET sys_unit_method = '{FROM_METHOD}'"
            f" WHERE source = '{SOURCE}' AND sys_reported_unit = '{EXPECTED_UNIT}'"
            f" AND sys_unit_method = '{TO_METHOD}';"
        ),
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

    Kept separate from :func:`plan` and off by default because the point of the
    dry run is that somebody reads it first. Records what it changed so the
    rollback is a fact rather than a reconstruction.
    """
    if tab_id not in TABS:
        return {"ok": False, "error": f"tab_not_eligible:{tab_id}"}
    if not confirm:
        return {"ok": False, "error": "confirm_required", "plan": plan(tab_id)}

    db.init()
    before = plan(tab_id, sample=0)
    eligible = before["rows_eligible"]
    if not eligible:
        return {"ok": True, "changed": 0, "already_done": True, "tab": tab_id}

    db.execute(
        f"UPDATE {_table(tab_id)} SET sys_unit_method = ?"
        f" WHERE {_PREDICATE}", (TO_METHOD,) + _ARGS)
    after = _count(tab_id, _PREDICATE, _ARGS)

    result = {
        "ok": True, "tab": tab_id, "changed": eligible - after,
        "still_assumed": after,
        "rollback_sql": before["rollback_sql"],
    }
    audit.record("unit_provenance_backfill", tab_id=tab_id, actor=actor,
                 detail={**result, "source": SOURCE, "from": FROM_METHOD, "to": TO_METHOD},
                 ok=True)
    return result


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
