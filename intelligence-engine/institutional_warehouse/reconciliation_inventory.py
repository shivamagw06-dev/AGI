"""What the fundamentals tabs actually contain, before anything is retired.

RELIANCE's June 2026 quarter is stored four times, under four labels, in three
magnitudes, by three sources. The obvious response - keep Upstox and Capital IQ,
drop the rest - is wrong until it has been checked, because a source can be
untrusted for a number and still be the only thing holding a period. Retiring it
on principle would delete history nothing else covers.

So this counts and shows. It never writes, never retires and never deletes.

What a group is
---------------
One company, one period - where "one period" means one ``period_key``, so
``Q1 FY27``, ``FY27Q1``, ``FY2027Q1`` and ``Jun 2026`` are the same group rather
than four.

Statement type is deliberately *not* part of the grouping key, and getting that
wrong the first time would have made this report dangerous. A consolidated and a
standalone filing are two real facts, so both have to survive - but ``UNKNOWN``
is not a third fact, it is a row whose type nobody recorded. Group by type and
every untyped row lands in its own group, looks like the only holder of
everything it contains, and is reported as un-retirable when the properly typed
row beside it covers the same quarter.

So the period is the group, and a winner is chosen per *known* statement type
within it. Consolidated and standalone both survive; untyped rows are measured
against them.

What the winner means
---------------------
The row the ownership contract would read: recent quarterly fundamentals from
Upstox, deep history from Capital IQ, and nothing promoted unless its period,
statement type, source and units are all known.

The number that decides whether a loser is safe to retire is not its source. It
is ``metrics_only_here``: the fields that row holds and no winner does. While
that list is non-empty, retiring the row loses data.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from institutional_warehouse import (canonical_rows, db, period_identity,
                                     unit_provenance, units)
from institutional_warehouse.schema import find_tab

#: Values worth comparing between two rows for the same period.
def _metric_fields(tab) -> tuple[str, ...]:
    extra = ("eps", "shares_outstanding", "book_value")
    return tuple(units.rescaled_columns(tab)) + extra

#: Two numbers this far apart describe different facts, not rounding.
TOLERANCE_PCT = 2.0

#: Preference among sources that are allowed to be canonical, per tab. Capital
#: IQ is the decade; Upstox is the live feed on top of it.
PREFERENCE: dict[str, tuple[str, ...]] = {
    "financials_annual": ("capital_iq_workbook", "capital_iq", "capiq",
                          "upstox", "upstox_fundamentals"),
    "financials_quarterly": ("upstox", "upstox_fundamentals",
                             "capital_iq_workbook", "capital_iq", "capiq"),
}

NO_CANDIDATE = "no_canonical_candidate"


def _statement_group(row: dict[str, Any]) -> str:
    """NULL and UNKNOWN are one identity. They were never two."""
    text = str(row.get("statement_type") or "").strip().upper()
    return text if text in canonical_rows.KNOWN_STATEMENT_TYPES else "UNKNOWN"


def _unit_of(row: dict[str, Any]) -> str:
    return str(row.get("sys_reported_unit") or "") or "unstamped"


def _unit_known(row: dict[str, Any]) -> bool:
    return canonical_rows.unit_is_known(row)


def _eligible(tab_id: str, row: dict[str, Any]) -> bool:
    """Whether this row could be read as the answer, on today's rules."""
    return not canonical_rows.blockers(tab_id, row, source=row.get("source"))


def _rank(tab_id: str, row: dict[str, Any]) -> int:
    order = PREFERENCE.get(tab_id, ())
    src = str(row.get("source") or "").strip().lower()
    return order.index(src) if src in order else len(order)


def _present(row: dict[str, Any], fields: Iterable[str]) -> set[str]:
    return {f for f in fields if row.get(f) is not None}


def _conflicting(winner: dict[str, Any], other: dict[str, Any],
                 fields: Iterable[str]) -> list[str]:
    """Fields where two comparable rows disagree by more than rounding.

    Only compared when both magnitudes are known. Comparing a normalised value
    against an unnormalised one measures the vendor's presentation, not the
    fact, and would report every field as a disagreement.
    """
    if not (_unit_known(winner) and _unit_known(other)):
        return []
    out: list[str] = []
    for field in fields:
        left, right = winner.get(field), other.get(field)
        if left is None or right is None:
            continue
        try:
            left, right = float(left), float(right)
        except (TypeError, ValueError):
            continue
        scale = max(abs(left), abs(right))
        if scale == 0:
            continue
        if abs(left - right) / scale * 100.0 > TOLERANCE_PCT:
            out.append(field)
    return out


def _row_view(row: dict[str, Any], tab_id: str, fields: tuple[str, ...]) -> dict[str, Any]:
    label = row.get(period_identity.PERIOD_FIELD[tab_id])
    return {
        "row_id": row.get("row_id"),
        "source": row.get("source"),
        "raw_label": label,
        "normalized_label": period_identity.canonical_label(label, tab_id=tab_id),
        "period_key": row.get("period_key") or period_identity.period_key(label),
        "statement_type": row.get("statement_type"),
        "units": _unit_of(row),
        "unit_method": row.get("sys_unit_method"),
        "unit_known": _unit_known(row),
        "revenue": row.get("revenue"),
        "pat": row.get("pat"),
        "assets": row.get("assets"),
        "metrics_present": len(_present(row, fields)),
        "eligible": _eligible(tab_id, row),
        "blockers": list(canonical_rows.blockers(tab_id, row, source=row.get("source"))),
    }


def inventory(tab_id: str, *, symbols: Optional[Iterable[str]] = None,
              max_groups_shown: int = 40,
              simulate_unit_provenance: bool = False) -> dict[str, Any]:
    """Group every row by period identity and say what would happen to it.

    Read-only. Returns counts for the whole tab, plus a sample of the groups
    that actually have something wrong with them.

    ``simulate_unit_provenance`` re-reads the same rows as though the Capital IQ
    provenance backfill had run, so its effect can be measured before production
    is written to. It applies the backfill's own predicate rather than a second
    description of it, and still writes nothing.
    """
    tab = find_tab(tab_id)
    if not tab or not canonical_rows.is_fundamental(tab_id):
        return {"ok": False, "error": f"not_a_fundamentals_tab:{tab_id}"}

    fields = _metric_fields(tab)
    wanted = {str(s).upper() for s in symbols} if symbols else None

    table = db.physical_table(tab_id)

    # Read one company at a time. These tabs hold 68,851 and 21,428 rows of
    # seventy columns each, and pulling them into one list to group in memory is
    # how this engine has taken itself down before. Grouping is per company
    # anyway, so nothing is lost by streaming.
    symbol_rows = db.query(
        f"SELECT DISTINCT symbol FROM {table} WHERE sys_published = 1 ORDER BY symbol")
    all_symbols = [str(r.get("symbol") or "") for r in symbol_rows]
    all_symbols = [s for s in all_symbols if s and (wanted is None or s.upper() in wanted)]

    st = _new_state(len(all_symbols))
    period_field = period_identity.PERIOD_FIELD[tab_id]
    for symbol in all_symbols:
        rows = db.query(
            f"SELECT * FROM {table} WHERE sys_published = 1 AND symbol = ?", (symbol,))
        if simulate_unit_provenance:
            rows = [_simulated(row) for row in rows]
        _ingest_symbol(tab_id, fields, period_field, symbol, rows, st, max_groups_shown)
    return _finalise(tab_id, st, bool(simulate_unit_provenance))


def _simulated(row: dict[str, Any]) -> dict[str, Any]:
    """One row as it would read after the provenance backfill. Writes nothing."""
    proposed = unit_provenance.simulated_method(row)
    return {**row, "sys_unit_method": proposed} if proposed else row


def _new_state(companies: int) -> dict[str, Any]:
    return {
        "totals": {
            "rows": 0, "companies": companies, "groups": 0, "duplicate_groups": 0,
            "rows_in_duplicate_groups": 0, "rows_that_survive": 0, "rows_retirable": 0,
            "rows_sole_holder_of_a_metric": 0, "groups_with_no_canonical_candidate": 0,
            "groups_with_value_conflicts": 0, "groups_with_mixed_units": 0,
            "rows_with_unknown_units": 0, "same_source_duplicate_rows": 0,
            "cross_source_duplicate_rows": 0, "raw_label_duplicate_groups": 0,
            "unknown_or_null_statement_type_rows": 0,
            "rows_in_groups_with_no_canonical_candidate": 0, "manual_review_rows": 0,
            "rows_with_unparseable_period": 0,
        },
        "by_source": {}, "by_unit": {}, "manual_review_ids": set(),
        "label_forms": set(), "blockers": {}, "samples": [],
    }


def _ingest_symbol(tab_id: str, fields, period_field: str, symbol: str,
                   rows: list[dict[str, Any]], st: dict[str, Any],
                   max_groups_shown: int) -> None:
    """Fold one company's rows into a running tally.

    Split out so a before/after can hand the identical row list to two tallies
    rather than reading the warehouse twice and comparing two different days.
    """
    totals = st["totals"]
    by_source = st["by_source"]
    by_unit = st["by_unit"]
    manual_review_ids = st["manual_review_ids"]
    label_forms = st["label_forms"]
    blocker_counts = st["blockers"]
    samples = st["samples"]
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        totals["rows"] += 1
        label = row.get(period_field)
        key = row.get("period_key") or period_identity.period_key(label)
        if not key:
            totals["rows_with_unparseable_period"] += 1
            key = f"UNPARSEABLE:{label}"
        groups.setdefault(str(key), []).append(row)

    totals["groups"] += len(groups)
    for key, members in sorted(groups.items()):
        members.sort(key=lambda r: (_rank(tab_id, r), not _eligible(tab_id, r),
                                    -len(_present(r, fields))))
        # One winner per real statement type. Consolidated and standalone are
        # two facts and both survive; UNKNOWN is not a third and wins nothing.
        winners: dict[str, dict[str, Any]] = {}
        for row in members:
            if not _eligible(tab_id, row):
                continue
            winners.setdefault(_statement_group(row), row)
        winners.pop("UNKNOWN", None)
        winner = next(iter(winners.values()), None)

        seen_sources: dict[str, int] = {}
        for row in members:
            src = str(row.get("source") or "unknown")
            seen_sources[src] = seen_sources.get(src, 0) + 1
            label_forms.add(str(row.get(period_field) or ""))
            bucket = by_source.setdefault(
                src, {"rows": 0, "eligible": 0, "unknown_units": 0})
            bucket["rows"] += 1
            bucket["eligible"] += 1 if _eligible(tab_id, row) else 0
            by_unit[_unit_of(row)] = by_unit.get(_unit_of(row), 0) + 1
            if not _unit_known(row):
                bucket["unknown_units"] += 1
                totals["rows_with_unknown_units"] += 1
            if _statement_group(row) == "UNKNOWN":
                bucket["unknown_statement_type"] = bucket.get("unknown_statement_type", 0) + 1
                totals["unknown_or_null_statement_type_rows"] += 1
            for code in canonical_rows.blockers(tab_id, row, source=row.get("source")):
                blocker_counts[code] = blocker_counts.get(code, 0) + 1

        same_source_dupes = sum(n - 1 for n in seen_sources.values() if n > 1)
        totals["same_source_duplicate_rows"] += same_source_dupes
        if len({_unit_of(r) for r in members}) > 1:
            totals["groups_with_mixed_units"] += 1
        if len({str(r.get(period_field) or "") for r in members}) > 1:
            totals["raw_label_duplicate_groups"] += 1
        if not winners:
            totals["groups_with_no_canonical_candidate"] += 1
            totals["rows_in_groups_with_no_canonical_candidate"] += len(members)
            # Nothing here can be trusted and nothing can be dropped on that
            # basis either. Every row is a person's decision.
            #
            # Counted by row id rather than incremented: a row in a group
            # with no candidate is also a sole holder of everything it
            # contains, so adding in both places counted the annual tab at
            # 137,617 of 68,866 rows - exactly twice - and made the number
            # unusable in the report it exists for.
            for row in members:
                manual_review_ids.add(str(row.get("row_id")))
        else:
            totals["rows_that_survive"] += len(winners)

        # Measured against everything that survives, not just one row: a
        # metric the consolidated winner lacks may be on the standalone one.
        winner_metrics: set[str] = set()
        for row in winners.values():
            winner_metrics |= _present(row, fields)
        kept = {id(row) for row in winners.values()}

        losers: list[dict[str, Any]] = []
        conflicts_here: list[str] = []
        for row in members:
            if id(row) in kept:
                continue
            only_here = sorted(_present(row, fields) - winner_metrics)
            if winners and str(row.get("source") or "") != str(
                    winner.get("source") or ""):
                totals["cross_source_duplicate_rows"] += 1
            if only_here:
                totals["rows_sole_holder_of_a_metric"] += 1
                # Holds something no survivor does, so retiring it loses
                # data. Whether that data is worth keeping is a judgement.
                manual_review_ids.add(str(row.get("row_id")))
            elif winners:
                totals["rows_retirable"] += 1
            disagrees = _conflicting(winner, row, fields) if winner is not None else []
            conflicts_here.extend(disagrees)
            view = _row_view(row, tab_id, fields)
            view["metrics_only_here"] = only_here
            view["conflicts_with_winner"] = disagrees
            losers.append(view)

        if conflicts_here:
            totals["groups_with_value_conflicts"] += 1
        if len(members) > 1:
            totals["duplicate_groups"] += 1
            totals["rows_in_duplicate_groups"] += len(members)

        if (len(members) > 1 or not winners) and len(samples) < max_groups_shown:
            samples.append({
                "symbol": symbol, "period_key": key,
                "rows": len(members),
                "sources": sorted(seen_sources),
                "same_source_duplicates": same_source_dupes,
                "winners": {stype: _row_view(row, tab_id, fields)
                            for stype, row in winners.items()},
                "winner_reason": (NO_CANDIDATE if winner is None
                                  else f"{winner.get('source')} is canonical for {tab_id}"),
                "losers": losers,
            })



def _finalise(tab_id: str, st: dict[str, Any], simulate: bool) -> dict[str, Any]:
    totals = st["totals"]
    by_source = st["by_source"]
    by_unit = st["by_unit"]
    manual_review_ids = st["manual_review_ids"]
    label_forms = st["label_forms"]
    blocker_counts = st["blockers"]
    samples = st["samples"]
    simulate_unit_provenance = simulate
    totals["manual_review_rows"] = len(manual_review_ids)
    return {
        "ok": True,
        "tab": tab_id,
        "dry_run": True,
        "simulated_unit_provenance": bool(simulate_unit_provenance),
        "totals": totals,
        "by_source": dict(sorted(by_source.items(), key=lambda kv: -kv[1]["rows"])),
        "by_unit": dict(sorted(by_unit.items(), key=lambda kv: -kv[1])),
        "blockers": dict(sorted(blocker_counts.items(), key=lambda kv: -kv[1])),
        "distinct_label_forms": len(label_forms),
        "label_forms": sorted(label_forms)[:60],
        "sample_groups": samples,
    }


def compare(tab_id: str, *, symbols: Optional[Iterable[str]] = None,
            max_groups_shown: int = 1) -> dict[str, Any]:
    """Before and after the provenance backfill over identical paired rows.

    The two halves of a before/after have to describe the same rows. Running the
    inventory twice against a live warehouse does not: schedulers write
    financials_annual every few minutes - derive_statement_columns alone
    accepted 55,134 rows in one pass - so the second read sees rows the first
    never did and the difference reads as an effect of the change when it is
    only the clock moving. That is what made an earlier comparison here look
    like 9,170 rows of source drift.

    Each company is read once and folded into both tallies, so every row counted
    in "after" is the same row counted in "before". This is deliberately not
    called a database snapshot: companies are streamed one at a time, so a live
    writer can change a company that has not yet been read. That does not alter
    the before/after delta for any row, but it means the aggregate is not a
    point-in-time picture of the whole table.
    """
    tab = find_tab(tab_id)
    if not tab or not canonical_rows.is_fundamental(tab_id):
        return {"ok": False, "error": f"not_a_fundamentals_tab:{tab_id}"}

    db.init()
    fields = _metric_fields(tab)
    wanted = {str(s).upper() for s in symbols} if symbols else None
    table = db.physical_table(tab_id)
    period_field = period_identity.PERIOD_FIELD[tab_id]

    all_symbols = [str(r.get("symbol") or "") for r in db.query(
        f"SELECT DISTINCT symbol FROM {table} WHERE sys_published = 1 ORDER BY symbol")]
    all_symbols = [s for s in all_symbols if s and (wanted is None or s.upper() in wanted)]

    before_st = _new_state(len(all_symbols))
    after_st = _new_state(len(all_symbols))
    for symbol in all_symbols:
        rows = db.query(
            f"SELECT * FROM {table} WHERE sys_published = 1 AND symbol = ?", (symbol,))
        _ingest_symbol(tab_id, fields, period_field, symbol, rows,
                       before_st, max_groups_shown)
        _ingest_symbol(tab_id, fields, period_field, symbol,
                       [_simulated(r) for r in rows], after_st, max_groups_shown)

    before = _finalise(tab_id, before_st, False)
    after = _finalise(tab_id, after_st, True)
    delta = {k: after["totals"][k] - v for k, v in before["totals"].items()
             if isinstance(v, int)}
    return {
        "ok": True, "dry_run": True, "tab": tab_id,
        "comparison_basis": "same_rows_per_symbol",
        "before_after_row_consistent": True,
        "whole_table_snapshot": False,
        "rows_compared": before["totals"]["rows"],
        "before": before["totals"], "after": after["totals"], "delta": delta,
        "before_by_source": before["by_source"], "after_by_source": after["by_source"],
    }


def inventory_all(*, symbols: Optional[Iterable[str]] = None,
                  max_groups_shown: int = 20,
                  simulate_unit_provenance: bool = False) -> dict[str, Any]:
    """The dry run across both fundamentals tabs. Writes nothing."""
    return {
        "ok": True,
        "dry_run": True,
        "simulated_unit_provenance": bool(simulate_unit_provenance),
        "tabs": {tab_id: inventory(tab_id, symbols=symbols,
                                   max_groups_shown=max_groups_shown,
                                   simulate_unit_provenance=simulate_unit_provenance)
                 for tab_id in sorted(period_identity.FUNDAMENTAL_TABS)},
    }
