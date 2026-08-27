"""Curated views over the warehouse, with the known-bad rows filtered out.

The warehouse holds good data and corrupt data in the same tables, and nothing
downstream can tell them apart without knowing the specific defect. Every
filter here corresponds to a defect verified against production on 2026-08-19:

* `financials_annual` carries two conventions at once. Rows labelled `FY2020`
  are annual figures in INR million; rows labelled `FY20` are *quarterly*
  figures in absolute rupees, with no statement_type. RELIANCE's `FY20` row
  shows a PAT of 63,480,000,000 - that is its Q4 FY20 result, not its year.
  128 symbols in a 4,000-row sample carry both, and the unit gap is a factor
  of a million, so a screen reading revenue without checking the label format
  can silently return a number a million times wrong.

* `daily_market_history` contains weekend rows. NSE does not trade then, and
  those bars carry a differently scaled series - MWL printed a tenth of its
  weekday price every Sunday for months before its split.

* `sector_ratio_history` marks rows the vendor already excluded from its own
  medians. Those stay excluded.

Nothing is deleted and nothing new is stored. Each view reports what it
rejected alongside what it kept, because a filter that quietly drops a quarter
of a table is indistinguishable from a filter that is broken.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Callable, Iterable, Optional

# Annual labels are four-digit; the two-digit form marks the contaminated rows.
_ANNUAL_LABEL = re.compile(r"^FY\d{4}$")
_QUARTERLY_LABEL = re.compile(r"^FY\d{2}$")


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _rows(tab: str, limit: int) -> list[dict[str, Any]]:
    try:
        from institutional_warehouse import store

        return list(store.all_rows(tab, limit=limit) or [])
    except Exception:
        return []


def _view(
    tab: str,
    limit: int,
    keep: Callable[[dict[str, Any]], Optional[str]],
    columns: tuple[str, ...],
) -> dict[str, Any]:
    """Apply one filter and report both sides of it.

    `keep` returns None for a good row, or a short reason string for a bad one.
    """
    kept: list[dict[str, Any]] = []
    rejected: dict[str, int] = {}
    for row in _rows(tab, limit):
        reason = keep(row)
        if reason is None:
            kept.append({c: row.get(c) for c in columns})
        else:
            rejected[reason] = rejected.get(reason, 0) + 1

    scanned = len(kept) + sum(rejected.values())
    return {
        "table": tab,
        "columns": list(columns),
        "rows": kept,
        "kept": len(kept),
        "scanned": scanned,
        "rejected": sum(rejected.values()),
        "rejected_pct": round(100.0 * sum(rejected.values()) / scanned, 2) if scanned else 0.0,
        "rejected_reasons": dict(sorted(rejected.items(), key=lambda kv: -kv[1])),
    }


def clean_financials_annual(limit: int = 5000) -> dict[str, Any]:
    """Annual statements with the mislabelled quarterly rows removed."""
    def keep(row: dict[str, Any]) -> Optional[str]:
        label = str(row.get("fiscal_year") or "").strip().upper()
        if _QUARTERLY_LABEL.match(label):
            return "quarterly_row_labelled_as_annual"
        if not _ANNUAL_LABEL.match(label):
            return "unrecognised_fiscal_year_label"
        if _num(row.get("revenue")) is None and _num(row.get("pat")) is None:
            return "no_revenue_or_pat"
        return None

    out = _view("financials_annual", limit, keep,
                ("symbol", "fiscal_year", "statement_type", "revenue", "ebitda", "pat", "eps"))
    out["units"] = "INR million"
    out["caveats"] = [
        "Capital IQ writes 0 for no-data; roughly a third of cells in the source "
        "workbook are zeros whose meaning depends on the metric, so a zero here "
        "is not evidence of a zero.",
        "No publication dates: the workbook carries fiscal year ends only, so "
        "point-in-time status is LIMITED and a filing lag must be assumed.",
    ]
    return out


def clean_daily_prices(limit: int = 5000) -> dict[str, Any]:
    """Price bars with non-trading days removed."""
    def keep(row: dict[str, Any]) -> Optional[str]:
        when = _as_date(row.get("date"))
        if when is None:
            return "unparseable_date"
        if when.weekday() >= 5:
            return "non_trading_day"
        close = _num(row.get("close"))
        if close is None or close <= 0:
            return "no_usable_close"
        return None

    out = _view("daily_market_history", limit, keep,
                ("symbol", "date", "open", "high", "low", "close", "volume"))
    out["caveats"] = [
        "adjusted_close is ignored: where populated it equals close and reflects "
        "no structural action, so it certifies nothing.",
        "Bars before the Upstox backfill reached a symbol may still be monthly.",
    ]
    return out


def clean_sector_ratios(limit: int = 20000) -> dict[str, Any]:
    """The ten-year Capital IQ ratio panel, vendor exclusions honoured."""
    def keep(row: dict[str, Any]) -> Optional[str]:
        if str(row.get("median_eligibility") or "").upper() != "ELIGIBLE":
            return "vendor_excluded_from_medians"
        if _num(row.get("value")) is None:
            return "no_value"
        if not str(row.get("fiscal_year") or "").strip():
            return "no_fiscal_year"
        return None

    out = _view("sector_ratio_history", limit, keep,
                ("symbol", "sector", "fiscal_year", "metric", "value"))
    out["caveats"] = [
        "Sector-specific metric sets: banks carry P/BV and P/TBV where "
        "industrials carry EV/EBITDA, so a metric absent for a company is "
        "usually inapplicable rather than missing.",
    ]
    return out


VIEWS: dict[str, Callable[..., dict[str, Any]]] = {
    "financials_annual": clean_financials_annual,
    "daily_prices": clean_daily_prices,
    "sector_ratios": clean_sector_ratios,
}


def view(name: str, limit: int = 5000) -> dict[str, Any]:
    builder = VIEWS.get(str(name or "").lower())
    if not builder:
        return {"ok": False, "error": "unknown_view", "available": sorted(VIEWS)}
    return {"ok": True, **builder(limit=limit)}


def summary(limit: int = 5000) -> dict[str, Any]:
    """Every view's headline numbers, for the admin index."""
    out = []
    for name, builder in VIEWS.items():
        try:
            result = builder(limit=limit)
        except Exception as exc:
            out.append({"view": name, "ok": False, "error": str(exc)[:160]})
            continue
        out.append({
            "view": name, "ok": True, "table": result["table"],
            "kept": result["kept"], "scanned": result["scanned"],
            "rejected": result["rejected"], "rejected_pct": result["rejected_pct"],
            "rejected_reasons": result["rejected_reasons"],
        })
    return {"ok": True, "views": out, "sample_limit": limit,
            "note": "Percentages describe the sampled rows, not the whole table."}
