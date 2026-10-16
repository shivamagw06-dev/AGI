"""Cross-source conflict detection.

Yahoo, Capital IQ, the Knowledge Factory and the statement engine all write the
same fields. Until now the last writer won silently on anything outside the
vendor-precedence list, which means a disagreement between sources looked
identical to agreement.

Disagreements are now recorded before the write, with both values and the source
of each. Nothing is discarded: the incoming value still lands, but the conflict
survives so a desk can see that two sources do not agree.

Comparison assumes both sides are on the same scale. Money columns reach that
state through ``units``; a stored row written before unit stamping existed has
no ``sys_reported_unit``, so comparing it against a normalised row would measure
the vendor's magnitude rather than the fact. Those rows are skipped on money
fields until ``units.backfill_units`` has migrated them.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse import db, statement_identity, store
from institutional_warehouse.schema import tab as get_tab
from institutional_warehouse.values import now_iso, to_number

# How far two numbers may differ before it counts as a disagreement rather than
# rounding. Vendors legitimately differ in the last decimal.
TOLERANCE_PCT = 2.0

# Fields where a difference is meaningful enough to record.
WATCHED_FIELDS = frozenset({
    "revenue", "ebitda", "pat", "eps", "equity", "debt", "cash", "assets",
    "shares_outstanding", "book_value", "close", "market_cap", "pe", "pb",
    "target_price", "promoter_holding",
})


def _materially_different(a: Any, b: Any) -> Optional[float]:
    """Percentage gap when two values genuinely disagree, else None."""
    left, right = to_number(a), to_number(b)
    if left is None or right is None:
        return None
    if left == right:
        return None
    scale = max(abs(left), abs(right))
    if scale == 0:
        return None
    gap = abs(left - right) / scale * 100.0
    return round(gap, 3) if gap > TOLERANCE_PCT else None


def detect(tab_id: str, rows: Sequence[dict[str, Any]], *, source: str,
           actor: str = "system") -> list[dict[str, Any]]:
    """Compare incoming rows against what is stored and record disagreements."""
    tab = get_tab(tab_id)
    watched = [c.key for c in tab.columns if c.key in WATCHED_FIELDS]
    if not watched:
        return []

    # Money columns are only comparable once both sides are in INR million.
    rescaled = {c.key for c in tab.columns if c.rescaled}

    found: list[dict[str, Any]] = []
    stamp = now_iso()
    payload: list[tuple[Any, ...]] = []
    skipped_unnormalised = 0

    for row in rows:
        row_id = store.make_row_id(tab, row)
        if not row_id:
            continue
        existing = store.raw_row(tab.id, row_id)
        if not existing:
            continue
        held_source = str(existing.get("source") or "")
        if not held_source or held_source == source:
            continue  # same source revising itself is a revision, not a conflict

        # A stored row with no unit stamp predates normalisation. Its money
        # columns may be in any magnitude, so a gap against a normalised row
        # says nothing about whether the sources actually disagree.
        held_unstamped = existing.get("sys_reported_unit") in (None, "")

        # Consolidated against standalone, or annual against quarterly, are
        # different facts. They should not collide on one row_id now that
        # statement_type is keyed, but a legacy row can still carry the wrong
        # pairing, and reporting that as a disagreement would be a false
        # conflict rather than a finding.
        if not statement_identity.comparable(existing, row):
            continue

        for field in watched:
            if held_unstamped and field in rescaled:
                skipped_unnormalised += 1
                continue
            if field not in row:
                continue
            gap = _materially_different(existing.get(field), row.get(field))
            if gap is None:
                continue
            entry = {
                "row_id": row_id,
                "tab_id": tab.id,
                "field": field,
                "held_value": existing.get(field),
                "held_source": held_source,
                "incoming_value": row.get(field),
                "incoming_source": source,
                "gap_pct": gap,
            }
            found.append(entry)
            payload.append((
                uuid.uuid4().hex, stamp, tab.id, row_id,
                str(existing.get("sys_entity") or ""), field,
                _text(existing.get(field)), held_source,
                _text(row.get(field)), source, gap, actor, 0,
            ))

    if payload:
        db.executemany(
            "INSERT INTO wh_conflicts (id, created_at, tab_id, row_id, entity, field,"
            " held_value, held_source, incoming_value, incoming_source, gap_pct, actor,"
            " resolved) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            payload,
        )
    if skipped_unnormalised:
        # Visible rather than silent: these comparisons are deferred until the
        # back-normalisation migration has stamped the stored rows.
        from institutional_warehouse import audit

        audit.record(
            "import",
            tab_id=tab.id,
            actor=actor,
            detail={
                "conflict_comparisons_deferred": skipped_unnormalised,
                "reason": "stored_row_has_no_unit_stamp",
                "remedy": "units.backfill_units",
                "incoming_source": source,
            },
        )
    return found


def _text(value: Any) -> Optional[str]:
    return None if value is None else str(value)


def recent(*, tab_id: Optional[str] = None, entity: Optional[str] = None,
           limit: int = 100) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if tab_id:
        clauses.append("tab_id = ?")
        params.append(tab_id)
    if entity:
        clauses.append("entity = ?")
        params.append(str(entity).upper())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.query(
        f"SELECT * FROM wh_conflicts{where} ORDER BY gap_pct DESC, created_at DESC LIMIT ?",
        (*params, max(1, min(int(limit), 500))),
    )
    return {
        "ok": True,
        "total": db.count("wh_conflicts", " AND ".join(clauses), params),
        "conflicts": [dict(r) for r in rows],
    }


def summary() -> dict[str, Any]:
    by_field = db.query(
        "SELECT field, COUNT(*) AS n, AVG(gap_pct) AS avg_gap FROM wh_conflicts"
        " GROUP BY field ORDER BY COUNT(*) DESC LIMIT 20"
    )
    by_pair = db.query(
        "SELECT held_source, incoming_source, COUNT(*) AS n FROM wh_conflicts"
        " GROUP BY held_source, incoming_source ORDER BY COUNT(*) DESC LIMIT 20"
    )
    return {
        "ok": True,
        "total": db.count("wh_conflicts"),
        "by_field": [{"field": r["field"], "count": int(r["n"] or 0),
                      "avg_gap_pct": round(float(r["avg_gap"] or 0), 2)} for r in by_field],
        "by_source_pair": [{"held": r["held_source"], "incoming": r["incoming_source"],
                            "count": int(r["n"] or 0)} for r in by_pair],
    }
