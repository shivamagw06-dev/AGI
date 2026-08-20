"""Warehouse Write Gateway — the one way data enters the warehouse.

Before this existed the validator protected humans and not collectors: the admin
paste path validated every row, while nineteen automated writes in the refresh
pipeline called ``store.upsert`` directly. That is how a return on equity of zero
and an earnings per share of 174 for a bank reached production.

Now every writer — collector, backfill, importer, formula engine — goes through
here:

    identity -> units -> missing-value intelligence -> validate -> conflicts
             -> persist -> quality -> audit

Identity runs first because a row cannot be keyed without it: ``statement_type``
is part of the natural key on the financial tabs, and a row with an empty key
part is skipped entirely.

Units run next because everything after them compares numbers. Crores against
rupees is a 10,000,000% gap, so a vendor reporting in a different magnitude
would otherwise fail validation ranges and register as a conflict on every
field.

Rejected rows are quarantined rather than dropped, so switching the collectors
onto a stricter path cannot silently lose data that used to land.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse import (
    audit, conflicts, db, missing_values, price_basis, quality, statement_identity,
    store, units, validation,
)
from institutional_warehouse.schema import find_tab
from institutional_warehouse.values import now_iso

# Writers that are allowed to skip validation entirely. Deliberately empty: the
# point of the gateway is that there is no such thing.
BYPASS_ALLOWED: frozenset[str] = frozenset()


def write(
    tab_id: str,
    rows: Iterable[dict[str, Any]],
    *,
    source: str,
    actor: str = "system",
    reason: Optional[str] = None,
    import_id: Optional[str] = None,
    require_reference: bool = False,
    detect_conflicts: bool = True,
    published: bool = True,
    reported_unit: Optional[str] = None,
    fill_only: bool = False,
) -> dict[str, Any]:
    """The single validated write path into the warehouse.

    ``fill_only`` marks the caller a gap-filler: it may add a row nobody has,
    and may never overwrite one somebody already wrote.
    """
    tab = find_tab(tab_id)
    if not tab:
        return {"ok": False, "error": f"unknown_tab:{tab_id}", "written": 0}

    incoming = [r for r in rows if isinstance(r, dict)]
    if not incoming:
        return {"ok": True, "tab": tab_id, "seen": 0, "written": 0, "inserted": 0,
                "updated": 0, "unchanged": 0, "quarantined": 0}

    # 0. What a price means, stamped by the feed that supplied it.
    #
    #    Three feeds write daily_market_history and they disagree about whether
    #    `close` is restated for splits. Done in the one write path rather than
    #    in each collector, so a new price source cannot forget and quietly
    #    inherit somebody else's convention.
    if tab_id == "daily_market_history":
        incoming = price_basis.stamp(incoming, source=source)

    # 1. Statement identity, before the row can be keyed at all: statement_type
    #    is part of the natural key, and a row with an empty key part is skipped.
    incoming = statement_identity.apply_identity(tab, incoming)

    # 2. Units, before anything reads a number. Aggregate money becomes INR
    #    million so validation ranges and conflict tolerances mean the same
    #    thing whichever vendor sent the row.
    unit_result = units.normalise_rows(tab_id, incoming, source=source,
                                       reported_unit=reported_unit)
    incoming = unit_result["rows"]

    # 3. Missing-value intelligence, before validation sees the row: a zero that
    #    means "absent" must not be validated as though it were a reading.
    cleaned: list[dict[str, Any]] = []
    reclassified = 0
    for row in incoming:
        verdict = missing_values.apply(row, source=source)
        cleaned.append(verdict["row"])
        reclassified += len(verdict["reclassified_zeros"])

    # 4. Validation. Rejected rows are quarantined, never silently dropped.
    report = validation.validate_payload(tab_id, cleaned, require_reference=require_reference)
    accepted = report["accepted"]
    quarantined = _quarantine(tab_id, report["rejected"], source=source, actor=actor,
                              import_id=import_id)

    # 5. Conflict detection against what is already stored.
    found_conflicts: list[dict[str, Any]] = []
    if quality.classify_source(source) == quality.CALCULATED:
        detect_conflicts = False
    if detect_conflicts and accepted:
        found_conflicts = conflicts.detect(tab_id, accepted, source=source, actor=actor)

    # 6. Persist.
    result = store.upsert(tab_id, accepted, source=source, actor=actor,
                          import_id=import_id, reason=reason, published=published,
                          fill_only=fill_only) \
        if accepted else {"inserted": 0, "updated": 0, "unchanged": 0, "skipped": 0}

    # 7. Unit and quality metadata for the rows that landed. Both are system
    #    columns, which store.upsert does not carry, so they are written here.
    _stamp_units(tab, accepted)
    stamped = _stamp_quality(tab, accepted, source=source,
                            conflicted={c["row_id"] for c in found_conflicts})

    audit.record(
        "import",
        tab_id=tab_id,
        actor=actor,
        detail={
            "gateway": True,
            "source": source,
            "seen": len(incoming),
            "accepted": len(accepted),
            "quarantined": quarantined,
            "reclassified_zeros": reclassified,
            "conflicts": len(found_conflicts),
            "unit": unit_result.get("unit"),
            "values_rescaled": unit_result.get("converted", 0),
            "reason": reason,
        },
        ok=quarantined == 0,
    )

    return {
        "ok": True,
        "tab": tab_id,
        "source": source,
        "seen": len(incoming),
        "written": len(accepted),
        "quarantined": quarantined,
        "reclassified_zeros": reclassified,
        "conflicts": len(found_conflicts),
        "quality_stamped": stamped,
        "warnings": report["warning_count"],
        "unit": unit_result.get("unit"),
        "values_rescaled": unit_result.get("converted", 0),
        # left_alone counts rows a gap-filler declined to overwrite. It is the
        # number that says the guard is doing something, so it is reported
        # rather than swallowed.
        **{k: result.get(k, 0)
           for k in ("inserted", "updated", "unchanged", "skipped", "left_alone")},
    }


def _quarantine(tab_id: str, rejected: Sequence[dict[str, Any]], *, source: str,
                actor: str, import_id: Optional[str]) -> int:
    """Rejected rows are kept, with the reason, so nothing disappears quietly."""
    if not rejected:
        return 0
    stamp = now_iso()
    payload = [
        (
            uuid.uuid4().hex,
            stamp,
            tab_id,
            source,
            actor,
            import_id,
            json.dumps(entry.get("key") or [], default=str),
            json.dumps(entry.get("issues") or [], default=str),
            json.dumps(entry, default=str)[:8000],
        )
        for entry in rejected
    ]
    db.executemany(
        "INSERT INTO wh_quarantine (id, created_at, tab_id, source, actor, import_id,"
        " row_key, issues, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        payload,
    )
    return len(payload)


def _stamp_units(tab, accepted: Sequence[dict[str, Any]]) -> int:
    """Persist the unit provenance the normaliser attached to each row.

    Without this the stamp never reaches the database, every stored row looks
    unnormalised to ``conflicts.detect``, and money comparisons are deferred
    forever.
    """
    if not accepted:
        return 0
    table = db.physical_table(tab.id)
    payload: list[tuple[Any, ...]] = []
    for row in accepted:
        unit = row.get("sys_reported_unit")
        if not unit:
            continue
        row_id = store.make_row_id(tab, row)
        if not row_id:
            continue
        payload.append((unit, row.get("sys_unit_scale"), row.get("sys_unit_method"), row_id))
    if payload:
        db.executemany(
            f"UPDATE {table} SET sys_reported_unit = ?, sys_unit_scale = ?,"
            f" sys_unit_method = ? WHERE row_id = ?",
            payload,
        )
    return len(payload)


def _stamp_quality(tab, accepted: Sequence[dict[str, Any]], *, source: str,
                   conflicted: set[str]) -> int:
    """Write quality type, confidence and validation status onto each stored row."""
    if not accepted:
        return 0
    table = db.physical_table(tab.id)
    material = [c.key for c in tab.columns
                if c.key not in ("source", "last_updated", "import_time")]
    payload: list[tuple[Any, ...]] = []
    stamp = now_iso()

    for row in accepted:
        row_id = store.make_row_id(tab, row)
        if not row_id:
            continue
        observed = sum(1 for key in material if row.get(key) is not None)
        missing = len(material) - observed
        block = quality.row_quality(
            source=source,
            observed_fields=observed,
            total_fields=len(material),
            missing_fields=missing,
            has_conflict=row_id in conflicted,
        )
        payload.append((block["quality_type"], block["confidence"], block["confidence_score"],
                        block["validation_status"], stamp, row_id))
    if payload:
        db.executemany(
            f"UPDATE {table} SET sys_quality = ?, sys_confidence = ?, sys_confidence_score = ?,"
            f" sys_validation = ?, sys_validated_at = ? WHERE row_id = ?",
            payload,
        )
    return len(payload)


def remediate_missing_zeros(*, actor: str = "system", tabs: Optional[Sequence[str]] = None,
                            dry_run: bool = False) -> dict[str, Any]:
    """Retire zeros already stored where a zero cannot be an observation.

    The gateway stops new ones arriving; rows written before it existed still
    carry them, and they are what made production narrate "return on equity rose
    from 0 in FY19".
    """
    from institutional_warehouse.schema import TABS

    wanted = [t for t in TABS if not tabs or t.id in set(tabs)]
    changed: dict[str, int] = {}
    detail: list[dict[str, Any]] = []

    for tab in wanted:
        table = db.physical_table(tab.id)
        fields = [c.key for c in tab.columns
                  if c.key in missing_values.ZERO_IS_MISSING and c.numeric]
        for field in fields:
            hits = db.count(table, f'"{field}" = 0')
            if not hits:
                continue
            changed[f"{tab.id}.{field}"] = hits
            detail.append({"tab": tab.id, "field": field, "rows": hits})
            if not dry_run:
                db.execute(f'UPDATE {table} SET "{field}" = NULL WHERE "{field}" = 0')

    total = sum(changed.values())
    if total and not dry_run:
        audit.record("recalculate", actor=actor,
                     detail={"remediation": "missing_zeros", "fields": changed, "rows": total})
    return {
        "ok": True,
        "dry_run": dry_run,
        "fields_touched": len(changed),
        "rows_changed": total,
        "detail": sorted(detail, key=lambda d: -d["rows"])[:40],
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def quarantined(tab_id: Optional[str] = None, limit: int = 100) -> dict[str, Any]:
    clause = " WHERE tab_id = ?" if tab_id else ""
    params: tuple[Any, ...] = (tab_id,) if tab_id else ()
    rows = db.query(
        f"SELECT id, created_at, tab_id, source, actor, row_key, issues FROM wh_quarantine"
        f"{clause} ORDER BY created_at DESC LIMIT ?",
        (*params, max(1, min(int(limit), 500))),
    )
    out = []
    for row in rows:
        out.append({
            **row,
            "row_key": _loads(row.get("row_key"), []),
            "issues": _loads(row.get("issues"), []),
        })
    return {"ok": True, "total": db.count("wh_quarantine", "tab_id = ?" if tab_id else "", params),
            "entries": out}


def quality_summary() -> dict[str, Any]:
    """Confidence and quality distribution across the warehouse."""
    from institutional_warehouse.schema import TABS

    out: dict[str, Any] = {}
    totals: dict[str, int] = {}
    for tab in TABS:
        table = db.physical_table(tab.id)
        try:
            rows = db.query(
                f"SELECT sys_quality AS quality, sys_confidence AS confidence, COUNT(*) AS n"
                f" FROM {table} GROUP BY sys_quality, sys_confidence"
            )
        except Exception:
            continue
        buckets = {}
        for row in rows:
            key = f"{row.get('quality') or 'unstamped'}/{row.get('confidence') or 'unstamped'}"
            buckets[key] = int(row.get("n") or 0)
            totals[key] = totals.get(key, 0) + int(row.get("n") or 0)
        if buckets:
            out[tab.id] = buckets
    stamped = sum(v for k, v in totals.items() if not k.startswith("unstamped"))
    total = sum(totals.values())
    return {
        "ok": True,
        "by_tab": out,
        "totals": totals,
        "rows_stamped": stamped,
        "rows_total": total,
        "stamped_pct": round(100.0 * stamped / total, 1) if total else 0.0,
        "quarantined": db.count("wh_quarantine"),
        "conflicts": db.count("wh_conflicts"),
    }


def _loads(raw: Any, fallback: Any) -> Any:
    try:
        return json.loads(raw) if raw else fallback
    except Exception:
        return fallback
