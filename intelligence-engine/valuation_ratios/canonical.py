"""The canonical read for the six Upstox ratios, with freshness that means something.

The existing read already prefers the newest row per ratio, so a company whose
refresh failed today is served yesterday's values rather than nulls. What it
never did was say so - and a stale number presented as a current one is worse
than a stale number labelled stale, because nobody can tell.

Two ideas do most of the work here.

Freshness belongs to the metric, not the company. A bank can have a perfectly
current snapshot in which EV/EBITDA is absent forever, because deposits are its
raw material and there is no enterprise value net of debt. Forcing one status to
describe the whole company makes that bank read as degraded every day of its
life. So each ratio carries its own state, and the company's state is derived
from them rather than imposed on them.

Newest valid is not newest. A row exists for a metric only when a value was
collected, so "the newest row" and "the newest row worth using" differ exactly
when something went wrong - which is the case this has to get right.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from valuation_ratios.ingest import PROVIDER_OWNED, SOURCE

FRESH = "FRESH"
PARTIAL_VALID = "PARTIAL_VALID"
STALE = "STALE"
NOT_APPLICABLE = "NOT_APPLICABLE"
INELIGIBLE = "INELIGIBLE"
UNAVAILABLE = "UNAVAILABLE"

# How many days old a value may be and still count as current. One covers a
# sweep that has not run yet today; beyond that the reader should know.
FRESH_WITHIN_DAYS = 1


def _latest_snapshot_date() -> Optional[str]:
    """The most recent day the sweep produced anything for anyone.

    Compared against, rather than the wall clock, because a value is not stale
    for being older than a sweep that has not happened.
    """
    from institutional_warehouse import db

    db.init()
    try:
        rows = db.query(
            f"SELECT MAX(reported_date) AS d FROM {db.physical_table('valuation_ratios')}")
    except Exception:
        return None
    return str((rows[0] if rows else {}).get("d") or "") or None


def _days_between(older: str, newer: str) -> Optional[int]:
    from datetime import datetime

    try:
        a = datetime.strptime(str(older)[:10], "%Y-%m-%d").date()
        b = datetime.strptime(str(newer)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return (b - a).days


def _metric_state(as_of: Optional[str], reference: Optional[str],
                  *, inapplicable: bool) -> str:
    if inapplicable and as_of is None:
        return NOT_APPLICABLE
    if as_of is None:
        return UNAVAILABLE
    if not reference:
        return FRESH
    gap = _days_between(as_of, reference)
    return FRESH if gap is not None and gap <= FRESH_WITHIN_DAYS else STALE


def company_state(metrics: dict[str, dict[str, Any]]) -> str:
    """One word for the company, derived from its metrics rather than replacing them.

    A metric that does not apply is not a gap and must not drag the company's
    state down; that is the whole reason banks needed this.
    """
    usable = {k: v for k, v in metrics.items() if v["status"] != NOT_APPLICABLE}
    if not usable:
        return NOT_APPLICABLE
    states = {v["status"] for v in usable.values()}
    if states == {FRESH}:
        return FRESH
    if states <= {UNAVAILABLE}:
        return UNAVAILABLE
    if STALE in states and not (states & {FRESH}):
        return STALE
    if UNAVAILABLE in states or STALE in states:
        return PARTIAL_VALID
    return FRESH


def canonical_ratios(symbol: str, *, reference_date: Optional[str] = None,
                     master: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """The six ratios as they should be shown, each with its own provenance."""
    from institutional_warehouse import store
    from valuation_ratios.sweep import ELIGIBLE_EQUITY, classify, inapplicable_for

    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "symbol_required"}

    row = master
    if row is None:
        found = store.fetch("company_master", filters={"symbol": ticker}, limit=1)
        row = ((found.get("rows") or [None]) or [None])[0] or {"symbol": ticker}

    eligibility = classify(row)
    if eligibility != ELIGIBLE_EQUITY:
        # An ETF has no earnings, so it has no P/E. Saying UNAVAILABLE would
        # imply the number exists and we failed to get it.
        return {"ok": True, "symbol": ticker, "status": INELIGIBLE,
                "eligibility": eligibility, "metrics": {}, "as_of": None}

    reference = reference_date or _latest_snapshot_date()
    na = inapplicable_for(row.get("sector"))

    rows = store.fetch("valuation_ratios", filters={"symbol": ticker},
                       limit=200).get("rows") or []
    # Newest first, so the first row seen for a metric is the newest one that
    # actually carries a value.
    rows.sort(key=lambda r: str(r.get("reported_date") or ""), reverse=True)

    metrics: dict[str, dict[str, Any]] = {}
    for record in rows:
        name = str(record.get("ratio_name") or "")
        if name not in PROVIDER_OWNED or name in metrics:
            continue
        if record.get("company_value") is None:
            continue
        as_of = str(record.get("reported_date") or "") or None
        metrics[name] = {
            "value": record.get("company_value"),
            "sector_value": record.get("sector_value"),
            "as_of": as_of,
            "status": _metric_state(as_of, reference, inapplicable=name in na),
            "source": record.get("source") or SOURCE,
            "snapshot_id": record.get("snapshot_id"),
        }

    for name in PROVIDER_OWNED:
        if name not in metrics:
            metrics[name] = {
                "value": None, "sector_value": None, "as_of": None,
                "status": NOT_APPLICABLE if name in na else UNAVAILABLE,
                "source": None, "snapshot_id": None,
            }

    dated = [m["as_of"] for m in metrics.values() if m["as_of"]]
    return {
        "ok": True,
        "symbol": ticker,
        "status": company_state(metrics),
        "eligibility": eligibility,
        "as_of": max(dated) if dated else None,
        "oldest_as_of": min(dated) if dated else None,
        "reference_date": reference,
        "metrics": metrics,
        "note": ("each ratio carries its own freshness; a company's status is "
                 "derived from them, and a ratio that does not apply to the "
                 "sector is not a gap"),
    }
