"""Financial statement identity — what makes one filing distinct from another.

A consolidated and a standalone filing for the same company and year are two
different facts, not two opinions about one fact. Until ``statement_type``
joined the natural key they hashed to the same row, so importing one silently
replaced the other with no conflict and no history.

What is in the key, and what is not
-----------------------------------
Key: ``symbol``, ``statement_type``, and the period.

``source`` is deliberately **not** in the key. Conflict detection works by
looking up the stored row that an incoming row collides with; if each vendor
owned its own row they would never collide, and DQIV could never report that
Yahoo and Upstox disagree. Sources share a row and disagreements are recorded.

``statement_version`` is also **not** in the key. Every write already snapshots
the prior row through ``versions``, so a restatement is a new snapshot on the
same identity rather than a second row. Putting the version in the key would
create a second version chain competing with the one that already exists.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from institutional_warehouse.schema import (
    DEFAULT_STATEMENT_TYPE,
    STATEMENT_FREQUENCIES,
    STATEMENT_TYPES,
    Tab,
)

#: Tab id to the frequency its rows carry when a vendor does not say.
TAB_FREQUENCY: dict[str, str] = {
    "financials_annual": "ANNUAL",
    "financials_quarterly": "QUARTERLY",
}

_TYPE_ALIASES: dict[str, str] = {
    "consolidated": "CONSOLIDATED",
    "consol": "CONSOLIDATED",
    "con": "CONSOLIDATED",
    "c": "CONSOLIDATED",
    "standalone": "STANDALONE",
    "stand_alone": "STANDALONE",
    "standalone_unconsolidated": "STANDALONE",
    "unconsolidated": "STANDALONE",
    "s": "STANDALONE",
}

_FREQUENCY_ALIASES: dict[str, str] = {
    "annual": "ANNUAL",
    "yearly": "ANNUAL",
    "fy": "ANNUAL",
    "quarterly": "QUARTERLY",
    "quarter": "QUARTERLY",
    "q": "QUARTERLY",
    "half_yearly": "HALF_YEARLY",
    "halfyearly": "HALF_YEARLY",
    "semi_annual": "HALF_YEARLY",
    "h1": "HALF_YEARLY",
    "ttm": "TTM",
    "trailing": "TTM",
}


def normalise_statement_type(raw: Any) -> str:
    """A vendor's statement-type label onto one of STATEMENT_TYPES.

    Anything unrecognised becomes UNKNOWN rather than being guessed: a filing
    filed under the wrong type is worse than one filed under none, because it
    would be compared against the wrong sibling.
    """
    text = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not text:
        return DEFAULT_STATEMENT_TYPE
    if text.upper() in STATEMENT_TYPES:
        return text.upper()
    return _TYPE_ALIASES.get(text, DEFAULT_STATEMENT_TYPE)


def normalise_frequency(raw: Any, *, tab_id: str = "") -> str:
    text = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if text and text.upper() in STATEMENT_FREQUENCIES:
        return text.upper()
    if text in _FREQUENCY_ALIASES:
        return _FREQUENCY_ALIASES[text]
    return TAB_FREQUENCY.get(tab_id, "UNKNOWN")


def applies_to(tab: Tab) -> bool:
    return "statement_type" in tab.key


def apply_identity(tab: Tab, rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill statement identity so a row can be keyed at all.

    ``statement_type`` is part of the key, and ``store.make_row_id`` refuses a
    row with an empty key part, so a collector that does not declare a type
    would otherwise have every row skipped.
    """
    if not applies_to(tab):
        return list(rows)

    out: list[dict[str, Any]] = []
    for row in rows:
        new_row = dict(row)
        new_row["statement_type"] = normalise_statement_type(
            row.get("statement_type") or row.get("type")
        )
        new_row["statement_frequency"] = normalise_frequency(
            row.get("statement_frequency") or row.get("frequency") or row.get("time_period"),
            tab_id=tab.id,
        )
        new_row.pop("type", None)
        new_row.pop("frequency", None)
        new_row.pop("time_period", None)
        out.append(new_row)
    return out


def comparable(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Whether two rows describe the same fact and may be compared.

    Consolidated against standalone, or annual against quarterly, are different
    facts. Reporting them as a disagreement would be a false conflict.
    """
    return (
        normalise_statement_type(left.get("statement_type"))
        == normalise_statement_type(right.get("statement_type"))
        and str(left.get("statement_frequency") or "")
        == str(right.get("statement_frequency") or "")
    )


def legacy_row_key(tab: Tab, values: dict[str, Any]) -> Optional[list[str]]:
    """The key parts this row would have had before statement_type joined them.

    Used by the migration to find rows whose stored ``row_id`` was hashed from
    the old key and therefore no longer matches what writers now compute.
    """
    if not applies_to(tab):
        return None
    parts = []
    for column in tab.key:
        if column == "statement_type":
            continue
        parts.append(str(values.get(column) or "").strip())
    return parts if all(parts) else None


# --------------------------------------------------------------------------
# Migration
# --------------------------------------------------------------------------


def unidentified_summary(tab_ids: Optional[Sequence[str]] = None) -> dict[str, Any]:
    """Stored statement rows that carry no statement type yet."""
    from institutional_warehouse import db
    from institutional_warehouse.schema import TABS

    out: dict[str, Any] = {}
    total = 0
    for tab in TABS:
        if not applies_to(tab) or (tab_ids and tab.id not in set(tab_ids)):
            continue
        table = db.physical_table(tab.id)
        try:
            missing = db.count(table, "statement_type IS NULL OR statement_type = ''")
            typed = db.count(table, "statement_type IS NOT NULL AND statement_type <> ''")
        except Exception:
            continue
        out[tab.id] = {"unidentified": missing, "identified": typed}
        total += missing
    return {"ok": True, "default_type": DEFAULT_STATEMENT_TYPE,
            "unidentified_total": total, "by_tab": out}


def backfill_identity(
    *,
    tab_ids: Optional[Sequence[str]] = None,
    dry_run: bool = True,
    actor: str = "system",
) -> dict[str, Any]:
    """Give stored rows a statement type and re-key them.

    Two things have to happen together. A row written before this change has no
    ``statement_type``, and its ``row_id`` was hashed from the old key — so a
    later import of the same filing would compute a different id, insert a
    second row, and neither would ever be recognised as the other's revision.

    Rows are stamped UNKNOWN rather than guessed. A later import that declares a
    type creates the correctly-typed row alongside, which is honest: we do not
    know whether the legacy figures were consolidated or standalone.
    """
    from institutional_warehouse import audit, db, store
    from institutional_warehouse.schema import TABS

    detail: list[dict[str, Any]] = []
    rows_typed = 0
    rows_rekeyed = 0
    collisions = 0

    for tab in TABS:
        if not applies_to(tab) or (tab_ids and tab.id not in set(tab_ids)):
            continue
        table = db.physical_table(tab.id)
        try:
            pending = db.query(
                f"SELECT * FROM {table} WHERE statement_type IS NULL OR statement_type = ''"
            )
        except Exception:
            continue
        if not pending:
            continue

        frequency = TAB_FREQUENCY.get(tab.id, "UNKNOWN")
        tab_rekeyed = 0
        tab_collisions = 0

        for raw in pending:
            values = dict(raw)
            values["statement_type"] = DEFAULT_STATEMENT_TYPE
            values.setdefault("statement_frequency", frequency)
            new_id = store.make_row_id(tab, values)
            old_id = str(raw.get("row_id") or "")
            if not new_id:
                continue
            rows_typed += 1
            if new_id == old_id:
                if not dry_run:
                    db.execute(
                        f"UPDATE {table} SET statement_type = ?, statement_frequency = ?"
                        f" WHERE row_id = ?",
                        (DEFAULT_STATEMENT_TYPE, values["statement_frequency"], old_id),
                    )
                continue

            # A row already sitting on the new id means this filing was
            # re-imported after the key change. Leave the newer row alone.
            clash = db.query(f"SELECT row_id FROM {table} WHERE row_id = ?", (new_id,))
            if clash:
                tab_collisions += 1
                collisions += 1
                continue

            tab_rekeyed += 1
            rows_rekeyed += 1
            if not dry_run:
                db.execute(
                    f"UPDATE {table} SET row_id = ?, statement_type = ?,"
                    f" statement_frequency = ? WHERE row_id = ?",
                    (new_id, DEFAULT_STATEMENT_TYPE, values["statement_frequency"], old_id),
                )

        detail.append({
            "tab": tab.id,
            "rows": len(pending),
            "rekeyed": tab_rekeyed,
            "already_keyed": len(pending) - tab_rekeyed - tab_collisions,
            "collisions_left_alone": tab_collisions,
            "statement_type": DEFAULT_STATEMENT_TYPE,
            "statement_frequency": frequency,
        })

    if rows_typed and not dry_run:
        audit.record("recalculate", actor=actor,
                     detail={"migration": "statement_identity", "rows": rows_typed,
                             "rekeyed": rows_rekeyed, "collisions": collisions})

    return {
        "ok": True,
        "dry_run": dry_run,
        "rows_typed": rows_typed,
        "rows_rekeyed": rows_rekeyed,
        "collisions_left_alone": collisions,
        "detail": detail,
    }
