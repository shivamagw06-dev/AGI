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


def _as_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if len(text) < 10 or not text[:4].isdigit():
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _newest(tab_id: str, column: str,
            value_columns: tuple[str, ...] = ()) -> tuple[Optional[date], int]:
    """The newest date the table can actually answer a question from.

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
        return None, 0
    if not total:
        return None, 0
    where = ""
    if value_columns:
        where = " WHERE " + " OR ".join(f"{c} IS NOT NULL" for c in value_columns)
    try:
        rows = db.query(f"SELECT MAX({column}) AS newest FROM {table}{where}")
    except Exception:
        # A column this table does not have must not silently report "never".
        try:
            rows = db.query(f"SELECT MAX({column}) AS newest FROM {table}")
        except Exception:
            return None, total
    return (_as_date((rows or [{}])[0].get("newest")), total)


def report(*, today: Optional[str] = None) -> dict[str, Any]:
    """One row per watched table: what it holds, and whether that is current."""
    now = _as_date(today) or datetime.now(timezone.utc).date()
    tables: list[dict[str, Any]] = []
    for tab_id, spec in sorted(EXPECTED.items()):
        newest, total = _newest(tab_id, spec["column"],
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
            "cadence": cadence,
            "rows": total,
            "newest": newest.isoformat() if newest else None,
            "age_days": age,
            "allowed_days": allowed,
            "status": status,
            "reader": spec.get("reader"),
            "note": spec.get("note"),
        })

    late = [t for t in tables if t["status"] in (LATE, EMPTY)]
    return {
        "ok": not late,
        "as_of": now.isoformat(),
        "watched": len(tables),
        "late": len(late),
        # Named so an alert can say which desk is affected rather than only
        # which table, because the table name means nothing to whoever reads it.
        "affected_readers": sorted({t["reader"] for t in late if t.get("reader")}),
        "tables": tables,
    }
