"""Validation engine — nothing invalid gets published.

Two levels:

* ``validate_payload`` runs before an import commits (missing values, invalid
  dates, duplicate companies, invalid symbols, impossible ratios, outlier
  multiples, broken references). Rejected rows never reach the tables.
* ``validate_tab`` audits what is already stored and drives the Data Quality tab.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse import db, store
from institutional_warehouse.schema import Tab, tab as get_tab
from institutional_warehouse.values import coerce, is_blank, normalise_entity, to_date, to_number

SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&._-]{0,24}$")
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")

# Bounds a value cannot cross and still describe reality. Breaking one of these
# rejects the row.
IMPOSSIBLE = {
    "dividend_yield": (0.0, 100.0),
    "promoter_holding": (0.0, 100.0),
    "institutional_holding": (0.0, 100.0),
    "fii": (0.0, 100.0),
    "dii": (0.0, 100.0),
    "mutual_funds": (0.0, 100.0),
    "insider_holding": (0.0, 100.0),
    "public_holding": (0.0, 100.0),
    "delivery_pct": (0.0, 100.0),
    "confidence": (0.0, 1.0),
    "pe": (-100000.0, 100000.0),
    "forward_pe": (-100000.0, 100000.0),
}

# Bounds that are possible but almost always mean a units or mapping error.
# Breaking one of these warns and still stores the row: a bank's other income or
# a one-off gain really can push a margin past 100%.
SUSPICIOUS = {
    "gross_margin": (-1000.0, 100.0),
    "ebitda_margin": (-1000.0, 100.0),
    "operating_margin": (-1000.0, 100.0),
    "net_margin": (-1000.0, 500.0),
    "roe": (-1000.0, 1000.0),
    "roa": (-500.0, 500.0),
    "pb": (-500.0, 1000.0),
    "ev_ebitda": (-500.0, 2000.0),
    "ev_sales": (-100.0, 1000.0),
    "price_sales": (-100.0, 1000.0),
}

OUTLIER = {
    "pe": 300.0,
    "ev_ebitda": 150.0,
    "ev_sales": 60.0,
    "pb": 60.0,
}

FRESHNESS_BUDGET_DAYS = {
    "daily_market_history": 5,
    "historical_valuation": 5,
    "consensus": 10,
    "company_master": 90,
    "financials_annual": 400,
    "financials_quarterly": 150,
}


def _issue(level: str, code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"level": level, "code": code, "message": message, **extra}


def _known_symbols() -> set[str]:
    try:
        return set(store.entities("company_master"))
    except Exception:
        return set()


def validate_row(
    tab: Tab,
    row: dict[str, Any],
    *,
    known_symbols: Optional[set[str]] = None,
    require_reference: bool = True,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    for key in tab.key:
        if is_blank(row.get(key)):
            issues.append(_issue("error", "missing_key", f"{key} is required", column=key))

    for column in tab.columns:
        if column.key not in row:
            continue
        raw = row.get(column.key)
        if is_blank(raw):
            if column.required:
                issues.append(_issue("error", "missing_required", f"{column.label} is required",
                                     column=column.key))
            continue
        value = coerce(column, raw)
        if column.numeric and value is None:
            issues.append(_issue("error", "not_a_number", f"{column.label} is not numeric: {raw!r}",
                                 column=column.key))
            continue
        if column.type == "date" and value is None:
            issues.append(_issue("error", "invalid_date", f"{column.label} is not a date: {raw!r}",
                                 column=column.key))
            continue
        if column.options and value is not None and str(value) not in column.options:
            issues.append(_issue("warn", "unknown_option",
                                 f"{column.label}={value!r} is outside {list(column.options)}",
                                 column=column.key))
        # Bounds only apply to numeric columns. Text fields that share a name
        # with a bounded metric (e.g. valuation_ratios.confidence = "high")
        # must not crash float() validation.
        if column.numeric and value is not None:
            try:
                number = float(value)
            except (TypeError, ValueError):
                number = None
            bounds = IMPOSSIBLE.get(column.key)
            if bounds is not None and number is not None:
                low, high = bounds
                if not (low <= number <= high):
                    issues.append(_issue("error", "impossible_value",
                                         f"{column.label}={value} outside [{low}, {high}]",
                                         column=column.key))
            soft = SUSPICIOUS.get(column.key)
            if soft is not None and number is not None:
                low, high = soft
                if not (low <= number <= high):
                    issues.append(_issue("warn", "suspicious_value",
                                         f"{column.label}={value} outside the usual [{low}, {high}]",
                                         column=column.key))
            threshold = OUTLIER.get(column.key)
            if threshold is not None and number is not None and abs(number) > threshold:
                issues.append(_issue("warn", "outlier", f"{column.label}={value} looks extreme",
                                     column=column.key))

    symbol = normalise_entity(row.get(tab.entity_column)) if tab.entity_column else None
    if symbol:
        if not SYMBOL_RE.match(symbol):
            issues.append(_issue("error", "invalid_symbol", f"symbol {symbol!r} is not a valid ticker",
                                 column=tab.entity_column))
        elif require_reference and tab.id != "company_master":
            pool = known_symbols if known_symbols is not None else _known_symbols()
            if pool and symbol not in pool:
                issues.append(_issue("warn", "broken_reference",
                                     f"{symbol} is not in Company Master",
                                     column=tab.entity_column))

    isin = row.get("isin")
    if not is_blank(isin) and not ISIN_RE.match(str(isin).strip().upper()):
        issues.append(_issue("warn", "invalid_isin", f"ISIN {isin!r} is malformed", column="isin"))

    # Indian shareholding convention: promoter + public = 100, and the
    # institutional buckets are a subset of public, not an addition to it.
    if tab.id == "ownership":
        promoter = to_number(row.get("promoter_holding"))
        public = to_number(row.get("public_holding"))
        if promoter is not None and public is not None and promoter + public > 105.0:
            issues.append(_issue("error", "impossible_ownership",
                                 f"promoter {promoter}% + public {public}% exceeds the float"))
        institutional = to_number(row.get("institutional_holding"))
        if institutional is not None and public is not None and institutional > public + 2.0:
            issues.append(_issue("warn", "ownership_mismatch",
                                 f"institutional {institutional}% exceeds public float {public}%"))
        fii, dii = to_number(row.get("fii")), to_number(row.get("dii"))
        if institutional is not None and fii is not None and dii is not None:
            if fii + dii > institutional + 2.0:
                issues.append(_issue("warn", "ownership_mismatch",
                                     f"FII+DII {round(fii + dii, 2)}% exceeds institutional {institutional}%"))

    # a trading day cannot have low > high
    if tab.id == "daily_market_history":
        low, high = to_number(row.get("low")), to_number(row.get("high"))
        if low is not None and high is not None and low > high:
            issues.append(_issue("error", "impossible_range", f"low {low} above high {high}"))
        close = to_number(row.get("close"))
        if close is not None and high is not None and low is not None and not (low <= close <= high):
            issues.append(_issue("warn", "close_outside_range", f"close {close} outside [{low}, {high}]"))
        traded = to_date(row.get("date"))
        if traded and traded > (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat():
            issues.append(_issue("error", "future_date", f"date {traded} is in the future", column="date"))

    if tab.id == "consensus":
        high, low = to_number(row.get("high_target")), to_number(row.get("low_target"))
        if high is not None and low is not None and low > high:
            issues.append(_issue("error", "impossible_range", f"low target {low} above high target {high}"))

    return issues


def validate_payload(
    tab_id: str,
    rows: Sequence[dict[str, Any]],
    *,
    require_reference: bool = True,
) -> dict[str, Any]:
    """Validate an import batch. Returns accepted rows and a rejection report."""
    tab = get_tab(tab_id)
    known = _known_symbols()
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen_keys: dict[tuple[str, ...], int] = {}
    duplicates = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            rejected.append({"index": index, "issues": [_issue("error", "bad_row", "row is not an object")]})
            continue
        issues = validate_row(tab, row, known_symbols=known, require_reference=require_reference)
        key = tuple(store.key_values(tab, row))
        if "" not in key:
            if key in seen_keys:
                duplicates += 1
                issues.append(_issue("error", "duplicate_key",
                                     f"duplicate of row {seen_keys[key]} for key {list(key)}"))
            else:
                seen_keys[key] = index
        errors = [i for i in issues if i["level"] == "error"]
        warns = [i for i in issues if i["level"] == "warn"]
        if warns:
            warnings.append({"index": index, "key": list(key), "issues": warns})
        if errors:
            rejected.append({"index": index, "key": list(key), "issues": errors})
        else:
            accepted.append(row)

    return {
        "ok": not rejected,
        "tab": tab.id,
        "seen": len(rows),
        "accepted": accepted,
        "accepted_count": len(accepted),
        "rejected": rejected,
        "rejected_count": len(rejected),
        "duplicates": duplicates,
        "warnings": warnings,
        "warning_count": len(warnings),
    }


# --------------------------------------------------------------------------
# Stored-data audit (Data Quality tab)
# --------------------------------------------------------------------------


def _freshness_label(tab_id: str, last_updated: Optional[str]) -> str:
    if not last_updated:
        return "never"
    try:
        stamp = datetime.fromisoformat(str(last_updated).replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    age_days = (datetime.now(timezone.utc) - stamp).days
    budget = FRESHNESS_BUDGET_DAYS.get(tab_id, 30)
    if age_days <= budget:
        return f"fresh ({age_days}d)"
    if age_days <= budget * 3:
        return f"stale ({age_days}d)"
    return f"expired ({age_days}d)"


def validate_tab(tab_id: str, *, sample: int = 500) -> dict[str, Any]:
    tab = get_tab(tab_id)
    stats = store.tab_stats(tab.id)
    rows = store.fetch(tab.id, limit=max(1, min(int(sample), 2000))).get("rows") or []
    known = _known_symbols()

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    missing_values = 0
    checked_cells = 0
    material = [c for c in tab.columns if c.key not in ("source", "last_updated", "import_time")]

    for row in rows:
        for column in material:
            checked_cells += 1
            if is_blank(row.get(column.key)):
                missing_values += 1
        issues = validate_row(tab, row, known_symbols=known)
        for issue in issues:
            entry = {**issue, "row_id": row.get("row_id")}
            (errors if issue["level"] == "error" else warnings).append(entry)

    if stats.get("rows", 0) == 0:
        status = "empty"
    elif errors:
        status = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "ok"

    return {
        "ok": status in ("ok", "warn", "empty"),
        "tab": tab.id,
        "status": status,
        "rows": stats.get("rows"),
        "companies": stats.get("companies"),
        "sampled": len(rows),
        "checked_cells": checked_cells,
        "missing_values": missing_values,
        "errors": errors[:200],
        "error_count": len(errors),
        "warnings": warnings[:200],
        "warning_count": len(warnings),
        "last_updated": stats.get("last_updated"),
        "freshness": _freshness_label(tab.id, stats.get("last_updated")),
    }


def validate_all(*, sample: int = 250) -> dict[str, Any]:
    from institutional_warehouse.schema import TABS

    reports = {}
    failed = []
    for tab in TABS:
        report = validate_tab(tab.id, sample=sample)
        reports[tab.id] = {
            "status": report["status"],
            "rows": report["rows"],
            "errors": report["error_count"],
            "warnings": report["warning_count"],
            "freshness": report["freshness"],
        }
        if report["status"] == "fail":
            failed.append(tab.id)
    return {"ok": not failed, "failed": failed, "tabs": reports}


def duplicate_companies() -> list[dict[str, Any]]:
    """Company Master rows that collide on symbol or ISIN."""
    rows = db.query(
        f"SELECT symbol, COUNT(*) AS n FROM {db.physical_table('company_master')}"
        " WHERE symbol IS NOT NULL GROUP BY symbol HAVING COUNT(*) > 1"
    )
    isins = db.query(
        f"SELECT isin, COUNT(*) AS n FROM {db.physical_table('company_master')}"
        " WHERE isin IS NOT NULL AND isin <> '' GROUP BY isin HAVING COUNT(*) > 1"
    )
    out = [{"kind": "symbol", "value": r.get("symbol"), "count": int(r.get("n") or 0)} for r in rows]
    out += [{"kind": "isin", "value": r.get("isin"), "count": int(r.get("n") or 0)} for r in isins]
    return out


def broken_references(limit: int = 100) -> list[dict[str, Any]]:
    """Entities present in a data tab but absent from Company Master."""
    known = _known_symbols()
    if not known:
        return []
    out = []
    from institutional_warehouse.schema import TABS

    for tab in TABS:
        if tab.id == "company_master" or not tab.entity_column:
            continue
        for symbol in store.entities(tab.id):
            if symbol not in known:
                out.append({"tab": tab.id, "symbol": symbol})
                if len(out) >= limit:
                    return out
    return out
