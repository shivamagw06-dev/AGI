"""What every table should hold by now, and what it actually holds.

Written after an audit found five tables silently stuck on 20 August. The
cause was one expired Upstox token in the web service, which drives corporate
actions, shareholding, company profiles and FII/DII. Nothing reported it: the
collectors failed per-company with 401s, the schedulers reported themselves
enabled, and the pages simply showed old numbers.

Staleness is measured against a declared cadence rather than a fixed number of
days, because the tables are not all daily. A fiscal-year archive that has not
moved since March 2025 is correct; a price table that has not moved since
Thursday is not, and a single threshold cannot tell them apart.

Two levels of check, because there are 85 tables and only some have a cadence
anyone has thought about:

  declared  -- a business-date column and a cadence, written down below. Asks
               "is the data current?" and is the check worth alerting on.
  derived   -- everything else, measured on whatever column records when a row
               was written. Asks only "is anything still writing here?", which
               needs no cadence to answer and still catches a dead collector.

The second kind exists because the first covered thirteen tables and the other
seventy-two could stop without anything noticing. A weak check on all of them
beats a sharp check on a sixth of them.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

DAILY = "daily"          # every trading day
WEEKLY = "weekly"
MONTHLY = "monthly"
EVENT = "event"          # arrives when something happens; absence is not failure
STATIC = "static"        # a frozen source archive; movement would be the surprise

# Only the tables something reads. A tab nobody consumes being empty is a
# different conversation from a tab the sector desk reads being stale.
EXPECTED: dict[str, dict[str, Any]] = {
    "daily_market_history": {"cadence": DAILY, "column": "date",
                             "reader": "prices, valuation, factors",
                             "value_columns": ("close",)},
    "valuation_ratios": {"cadence": DAILY, "column": "reported_date",
                         "reader": "valuation desk, workbook",
                         "value_columns": ("company_value",)},
    "historical_valuation": {"cadence": DAILY, "column": "date",
                             "reader": "sector intelligence, factor layer",
                             "value_columns": ("pe", "pb", "cmp")},
    "institutional_flow": {"cadence": DAILY, "column": "date",
                           "reader": "market intelligence flows panel",
                           # A flow row with neither side populated is a date,
                           # not an observation. One reached the table from an
                           # empty test POST and made the feed read as current
                           # while carrying nothing.
                           "value_columns": ("fii_net", "dii_net")},
    "historical_sector_medians": {"cadence": DAILY, "column": "as_of",
                                  "reader": "sector valuation explorer"},
    "corporate_actions": {"cadence": EVENT, "column": "effective_date",
                          "reader": "price adjustment, hedge fund lab",
                          "quiet_days": 7},
    "insider_trades": {"cadence": EVENT, "column": "reported_on",
                       "reader": "insider activity", "quiet_days": 5},
    "ownership": {"cadence": WEEKLY, "column": "as_of",
                  "reader": "ownership intelligence"},
    "peer_relationships": {"cadence": WEEKLY, "column": "as_of",
                           "reader": "knowledge factory, peers"},
    "consensus": {"cadence": MONTHLY, "column": "last_updated",
                  "reader": "broker estimates"},
    "financials_annual": {"cadence": EVENT, "column": "last_updated",
                          "reader": "factor layer, valuation", "quiet_days": 45},
    "financials_quarterly": {"cadence": EVENT, "column": "last_updated",
                             "reader": "statements", "quiet_days": 45},
    "sector_ratio_history": {"cadence": STATIC, "column": "as_of",
                             "reader": "historical percentiles",
                             "note": "CapIQ fiscal-year archive; frozen on purpose"},
}

# How many days without a new row before a cadence is considered late. Daily
# allows for a weekend plus a public holiday, because a Tuesday after a long
# weekend is not a broken collector.
TOLERANCE = {DAILY: 4, WEEKLY: 10, MONTHLY: 40, EVENT: 14, STATIC: 10_000}

OK = "ok"
LATE = "late"
EMPTY = "empty"
UNKNOWN = "unknown"
SILENT = "silent"            # derived: nothing has written here in a long time
UNWATCHABLE = "unwatchable"  # derived: no column records when a row was written

# Where to look for "when was this row written", best first. last_updated is on
# 76 of the 85 tables; the rest carry one of the others. Deliberately not a
# business date -- max(listing_date) on company_master is the newest listing,
# not a sign the table is alive, and reading it as one is how a monitor comes
# to report a dead table healthy.
AUDIT_COLUMNS = ("last_updated", "created_at", "as_of", "started_at",
                 "captured_at", "updated_at")

# A derived check has no cadence to compare against, so it only asks whether a
# table has gone quiet for longer than any collector plausibly should. Set well
# past monthly on purpose: a threshold that fires on ordinary gaps trains people
# to ignore the report, which is worse than not having it.
SILENT_AFTER_DAYS = 45


def _as_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if len(text) < 10 or not text[:4].isdigit():
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _newest(tab_id: str, column: str,
            value_columns: tuple[str, ...] = ()
            ) -> tuple[Optional[date], Optional[date], int]:
    """The newest and oldest dates the table can answer a question from.

    Both ends, because they fail differently. The newest answers "has ingestion
    stopped". The oldest answers "has history disappeared", and nothing was
    asking it -- a table truncated from behind keeps a fresh newest row and
    reports healthy while the past quietly goes missing.

    Not simply MAX(date): a row carrying only a date is not an observation,
    and one of those is enough to make a dead feed read as current. An empty
    POST to the flows ingest put exactly such a row at the top of
    institutional_flow, and the first version of this monitor reported the
    table healthy because of it.
    """
    from institutional_warehouse import db

    table = db.physical_table(tab_id)
    try:
        total = db.count(table)
    except Exception:
        return None, None, 0
    if not total:
        return None, None, 0
    where = ""
    if value_columns:
        where = " WHERE " + " OR ".join(f"{c} IS NOT NULL" for c in value_columns)
    try:
        rows = db.query(f"SELECT MAX({column}) AS newest, MIN({column}) AS oldest "
                        f"FROM {table}{where}")
    except Exception:
        # A column this table does not have must not silently report "never".
        try:
            rows = db.query(f"SELECT MAX({column}) AS newest, "
                            f"MIN({column}) AS oldest FROM {table}")
        except Exception:
            return None, None, total
    first = (rows or [{}])[0]
    return (_as_date(first.get("newest")), _as_date(first.get("oldest")), total)


def _audit_column(tab_id: str) -> Optional[str]:
    """The column recording when a row was written, or None if there is none."""
    try:
        from institutional_warehouse import schema
        tab = schema.find_tab(tab_id)
    except Exception:
        return None
    if tab is None:
        return None
    present = {c.key for c in tab.columns}
    for candidate in AUDIT_COLUMNS:
        if candidate in present:
            return candidate
    return None


def _derived_row(tab_id: str, now: date) -> dict[str, Any]:
    """A table nobody declared a cadence for: is anything still writing to it?

    Deliberately not an opinion about whether the data is current -- that needs
    a cadence and a business date. This only separates a table being filled
    from one that stopped, which is the failure that went unnoticed before.
    """
    from institutional_warehouse import db

    column = _audit_column(tab_id)
    try:
        total = db.count(db.physical_table(tab_id))
    except Exception:
        total = 0

    row = {"tab": tab_id, "cadence": None, "rows": total, "check": "derived",
           "column": column, "newest": None, "oldest": None,
           "span_days": None, "age_days": None,
           "allowed_days": SILENT_AFTER_DAYS, "reader": None, "note": None}

    if not total:
        # Empty and never declared is not automatically wrong: some tables are
        # for work that has not started. Reported, not alarmed about.
        row["status"] = EMPTY
        return row
    if not column:
        row["status"] = UNWATCHABLE
        row["note"] = "no column records when a row was written"
        return row

    newest, oldest, _ = _newest(tab_id, column)
    if newest is None:
        row["status"] = UNKNOWN
        return row
    age = (now - newest).days
    row["newest"] = newest.isoformat()
    row["oldest"] = oldest.isoformat() if oldest else None
    row["span_days"] = (newest - oldest).days if oldest else None
    row["age_days"] = age
    row["status"] = SILENT if age > SILENT_AFTER_DAYS else OK
    return row


def report(*, today: Optional[str] = None) -> dict[str, Any]:
    """One row per watched table: what it holds, and whether that is current."""
    now = _as_date(today) or datetime.now(timezone.utc).date()
    tables: list[dict[str, Any]] = []
    for tab_id, spec in sorted(EXPECTED.items()):
        newest, oldest, total = _newest(tab_id, spec["column"],
                                        tuple(spec.get("value_columns") or ()))
        age = (now - newest).days if newest else None
        cadence = spec["cadence"]
        allowed = spec.get("quiet_days", TOLERANCE[cadence])
        if not total:
            status = EMPTY
        elif newest is None:
            status = UNKNOWN
        elif age is not None and age > allowed:
            status = LATE
        else:
            status = OK
        tables.append({
            "tab": tab_id,
            "check": "declared",
            "cadence": cadence,
            "rows": total,
            "newest": newest.isoformat() if newest else None,
            "oldest": oldest.isoformat() if oldest else None,
            # How much past the table actually holds. A span that shrinks
            # between runs is history being lost, which a fresh newest row
            # hides completely.
            "span_days": (newest - oldest).days if newest and oldest else None,
            "age_days": age,
            "allowed_days": allowed,
            "status": status,
            "reader": spec.get("reader"),
            "note": spec.get("note"),
        })

    late = [t for t in tables if t["status"] in (LATE, EMPTY)]

    # Every remaining table, so that a collector stopping is visible even where
    # nobody has declared what current looks like.
    try:
        from institutional_warehouse import schema
        every = schema.tab_ids()
    except Exception:
        every = []
    derived = [_derived_row(t, now) for t in every if t not in EXPECTED]
    silent = [t for t in derived if t["status"] == SILENT]

    tables = tables + derived
    return {
        # Unchanged meaning: the declared checks are the ones worth waking for.
        "ok": not late,
        "as_of": now.isoformat(),
        "watched": len(tables),
        "late": len(late),
        # Named so an alert can say which desk is affected rather than only
        # which table, because the table name means nothing to whoever reads it.
        "affected_readers": sorted({t["reader"] for t in late if t.get("reader")}),
        # A table that stopped being written to. Separate from `late` because it
        # is a weaker claim, and mixing the two would let noise from seventy-two
        # tables drown the thirteen that have a real cadence behind them.
        "silent": [t["tab"] for t in silent],
        # Built, wired into the schema, never filled. Twenty-five of these on
        # the day this was written -- the whole macro layer, the whole portfolio
        # layer, every strategy table. Not an alert, because none of them broke;
        # they were never started. But invisible was the wrong way to hold it.
        "never_filled": [t["tab"] for t in derived if t["status"] == EMPTY],
        "coverage": {
            "tables": len(tables),
            "declared": len(EXPECTED),
            "derived": len(derived),
            "unwatchable": sum(1 for t in derived if t["status"] == UNWATCHABLE),
        },
        "tables": tables,
    }
