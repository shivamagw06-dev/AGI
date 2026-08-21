"""Who is allowed to write what, enforced rather than remembered.

Every data defect this warehouse has produced came from the same shape: two
sources writing one field with no rule about which was authoritative.

A raw traded price and a split-adjusted one shared the `close` column, and the
last writer won - Dr. Lal PathLabs was published at -45% for a year it finished
up 9.4%. A market-cap update rewrote the `source` column on 389,682 rows and
erased which feed had supplied their prices. The bhavcopy walker re-collected
days Upstox had already priced and replaced adjusted values with raw ones.

None of those were bad code. Each writer was correct about its own data. What
was missing was a statement of who owns the field, and something to enforce it.

Two principles decide every rule below:

* A shallower source may enrich a deeper one and may never truncate it. Upstox
  returns four annual periods; Capital IQ holds ten. Fresher is not deeper.
* A source that only knows about tradeable instruments cannot be allowed to
  decide that a delisted company never existed.

Violations are rejected and recorded. They are not resolved by precedence order,
because a silent resolution is how a wrong number reaches a client with nobody
having chosen it.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

# --------------------------------------------------------------------------
# Source properties
# --------------------------------------------------------------------------

# A source that reports only the present. It may write recent periods and must
# never rewrite history: Upstox's six key ratios are today's values with no time
# dimension at all, so a row of them dated FY2019 would be a fabrication.
CURRENT_ONLY = "current_only"

# A source that may add rows nobody has and may never change one somebody else
# wrote. The bhavcopy is the only place a delisted company still has a price,
# and the wrong authority on a day another feed has already priced.
FILL_ONLY = "fill_only"

# A source holding history no other source can supply. It cannot be retired
# while it is the only holder of a period.
DEEP_HISTORY = "deep_history"

SOURCE_ROLES: dict[str, frozenset[str]] = {
    "upstox_key_ratios": frozenset({CURRENT_ONLY}),
    "upstox": frozenset({CURRENT_ONLY}),
    "nse_bhavcopy": frozenset({FILL_ONLY, DEEP_HISTORY}),
    "capital_iq_workbook": frozenset({DEEP_HISTORY}),
    "capital_iq": frozenset({DEEP_HISTORY}),
}

# --------------------------------------------------------------------------
# Field ownership
# --------------------------------------------------------------------------
#
# (tab, field) -> the sources allowed to write it. A field absent from this map
# is unowned and anyone may write it; only the contested fields are listed,
# because declaring every column would rot faster than it helps.

_OWNERS: dict[tuple[str, str], frozenset[str]] = {}


def _own(tab: str, fields: Iterable[str], owners: Iterable[str]) -> None:
    allowed = frozenset(owners)
    for field in fields:
        _OWNERS[(tab, field)] = allowed


# Ratios computed from statements. Upstox supplies none of these - its Key
# Ratios endpoint returns six values and none of them are margins, turnover,
# coverage or liquidity - so a write from Upstox here is a mistake by
# definition, not a difference of opinion.
_own("historical_ratios",
     ("gross_margin", "operating_margin", "net_margin", "fcf_margin",
      "asset_turnover", "interest_coverage", "current_ratio", "quick_ratio",
      "debt_equity"),
     {"formula_engine"})

# The three that do overlap. Upstox owns the current value; the historical
# series stays with whoever computed it from statements. They live in different
# tables, so this is about keeping them there.
_own("historical_ratios", ("roe", "roa", "roce"), {"formula_engine"})

# Prices. The basis column is what keeps raw and adjusted apart; ownership keeps
# the wrong writer from filling it in.
_own("daily_market_history", ("price_basis", "feed_family"),
     {"upstox_v3_historical", "upstox_v3_daily", "upstox_v3", "upstox",
      "nse_bhavcopy", "yahoo_finance", "yahoo_finance_history"})


def owners_of(tab: str, field: str) -> Optional[frozenset[str]]:
    return _OWNERS.get((tab, field))


def has_role(source: Any, role: str) -> bool:
    return role in SOURCE_ROLES.get(str(source or "").strip().lower(), frozenset())


def deep_history_sources() -> tuple[str, ...]:
    return tuple(sorted(s for s, r in SOURCE_ROLES.items() if DEEP_HISTORY in r))


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

# How far back a current-only source may write. A quarter of slack covers a
# late filing and a fiscal-year boundary; anything older is history, and history
# is not what a snapshot of today knows about.
CURRENT_PERIOD_SLACK_DAYS = 120


def _violation(rule: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"rule": rule, "detail": detail, **extra}


def check_fields(tab: str, rows: Iterable[dict[str, Any]], *, source: str) -> list[dict[str, Any]]:
    """Fields this source is not allowed to write.

    Reported per field rather than per row: one misconfigured collector produces
    the same violation thousands of times and a thousand identical messages
    hides the one that matters.
    """
    src = str(source or "").strip().lower()
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for field, value in row.items():
            if field in seen or value is None:
                continue
            allowed = owners_of(tab, field)
            if allowed is None or src in allowed:
                continue
            seen.add(field)
            out.append(_violation(
                "field_not_owned",
                f"{src} may not write {tab}.{field}; owned by {', '.join(sorted(allowed))}",
                tab=tab, field=field, source=src, owners=sorted(allowed)))
    return out


# Where a source is snapshot-only, which is a fact about the endpoint rather
# than the vendor.
#
# Upstox is both things at once. Its Key Ratios endpoint returns six values with
# no time dimension, so a row of them dated to an old fiscal year is invented.
# Its statement endpoints return four real annual periods, and a refresh of
# FY2023 is exactly what they are for. Marking the vendor current-only would
# have blocked the statements project outright.
CURRENT_ONLY_TABS: dict[str, frozenset[str]] = {
    "upstox": frozenset({"valuation_ratios"}),
    "upstox_key_ratios": frozenset({"valuation_ratios"}),
}


def is_current_only(source: Any, tab: str) -> bool:
    key = str(source or "").strip().lower()
    if not has_role(key, CURRENT_ONLY):
        return False
    scoped = CURRENT_ONLY_TABS.get(key)
    return True if scoped is None else tab in scoped


def check_period_scope(tab: str, rows: Iterable[dict[str, Any]], *, source: str,
                       today: Optional[str] = None) -> list[dict[str, Any]]:
    """A source that only knows about the present writing about the past.

    Scoped to the endpoint, not the vendor: Upstox key ratios carry no time
    dimension, while Upstox statements carry four real annual periods.
    """
    if not is_current_only(source, tab):
        return []
    from datetime import date, datetime, timedelta

    anchor = (datetime.strptime(today, "%Y-%m-%d").date() if today
              else datetime.now().date())
    cutoff = anchor - timedelta(days=CURRENT_PERIOD_SLACK_DAYS)
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        # reported_date is what valuation_ratios actually calls its date column.
        # Without it the check silently never applied to the one tab it was
        # written for.
        for key in ("snapshot_date", "reported_date", "date", "as_of", "period_end"):
            raw = str(row.get(key) or "").strip()
            if not raw:
                continue
            try:
                when = datetime.strptime(raw[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            if when < cutoff:
                out.append(_violation(
                    "current_source_writing_history",
                    f"{source} reports only the present and cannot write {key}={raw}",
                    tab=tab, source=str(source), field=key, value=raw,
                    cutoff=cutoff.isoformat()))
            break
    return out


def check_price_basis(rows: Iterable[dict[str, Any]], *, source: str) -> list[dict[str, Any]]:
    """A price stamped with a basis its source does not produce.

    Catches a writer mislabelling its own data, which is the failure the basis
    column exists to prevent and would otherwise reintroduce silently.
    """
    from institutional_warehouse import price_basis as pb

    _, expected = pb.describe(source)
    if expected == pb.UNKNOWN:
        return []
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict) or row.get("close") is None:
            continue
        stated = str(row.get("price_basis") or "").upper()
        if stated and stated != expected:
            out.append(_violation(
                "price_basis_mismatch",
                f"{source} produces {expected} prices but the row claims {stated}",
                source=str(source), expected=expected, stated=stated))
            break
    return out


def check_canonical_claim(tab: str, rows: Iterable[dict[str, Any]],
                         *, source: str) -> list[dict[str, Any]]:
    """A source marking its own rows canonical when it is not trusted for them.

    The flag decides which of four rows for one quarter a reader believes, so a
    collector that sets it on the way in has quietly appointed itself the
    authority. It is derived at the gateway from what is actually known about
    the row; asserting it is a violation rather than a preference.
    """
    from institutional_warehouse import canonical_rows

    if not canonical_rows.is_fundamental(tab):
        return []
    if canonical_rows.source_is_canonical(tab, source):
        return []
    for row in rows or []:
        if isinstance(row, dict) and row.get("is_canonical"):
            allowed = ", ".join(sorted(canonical_rows.canonical_sources(tab)))
            return [_violation(
                "canonical_claim_not_owned",
                f"{source} may not write canonical {tab} rows; canonical sources are {allowed}",
                tab=tab, source=str(source),
                owners=sorted(canonical_rows.canonical_sources(tab)))]
    return []


def check(tab: str, rows: Iterable[dict[str, Any]], *, source: str,
          today: Optional[str] = None) -> list[dict[str, Any]]:
    """Everything the contract forbids about this write."""
    rows = list(rows or [])
    return (check_fields(tab, rows, source=source)
            + check_period_scope(tab, rows, source=source, today=today)
            + check_canonical_claim(tab, rows, source=source)
            + (check_price_basis(rows, source=source)
               if tab == "daily_market_history" else []))


def strip_null_overwrites(rows: Iterable[dict[str, Any]],
                          existing: dict[str, dict[str, Any]],
                          *, key_of: Any) -> tuple[list[dict[str, Any]], int]:
    """Drop explicit nulls that would erase a value already stored.

    A refresh that fails and returns nothing must leave the last good value
    alone. Writing the null is how a working figure becomes a blank on the desk
    because a vendor had a bad morning.
    """
    kept: list[dict[str, Any]] = []
    dropped = 0
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        prior = existing.get(key_of(row)) or {}
        if not prior:
            kept.append(row)
            continue
        cleaned = dict(row)
        for field, value in list(row.items()):
            if value is None and prior.get(field) is not None:
                cleaned.pop(field, None)
                dropped += 1
        kept.append(cleaned)
    return kept, dropped


def sole_holder_periods(tab: str, source: str, *, period_field: str = "date") -> int:
    """How many periods only this source covers.

    A source cannot be retired while it is the only thing standing between the
    warehouse and a hole. The bhavcopy is the only place a delisted company has
    a price; retiring it as redundant would delete the survivorship record that
    every honest backtest depends on.
    """
    from institutional_warehouse import db

    db.init()
    table = db.physical_table(tab)
    try:
        rows = db.query(
            f"SELECT COUNT(*) AS n FROM ("
            f"  SELECT \"{period_field}\" FROM {table}"
            f"  GROUP BY \"{period_field}\""
            f"  HAVING SUM(CASE WHEN source = ? THEN 1 ELSE 0 END) = COUNT(*)"
            f")", (source,))
    except Exception:
        return 0
    return int((rows[0] if rows else {}).get("n") or 0)
