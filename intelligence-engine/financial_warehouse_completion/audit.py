"""Phase 7.4F Step 0 — Financial Warehouse Coverage Audit (read-only).

Measures what the Institutional Warehouse already holds before any CapIQ /
provider backfill. Never writes.
"""

from __future__ import annotations

import re
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from financial_warehouse_completion.models import ENGINE_CODE, PROGRAMME_CODE, PROGRAMME_VERSION

# Classification thresholds (annual years / quarterly periods).
CLASS_COMPLETE_10Y = "COMPLETE_10Y"
CLASS_GOOD = "GOOD"
CLASS_PARTIAL = "PARTIAL"
CLASS_MINIMAL = "MINIMAL"
CLASS_EMPTY = "EMPTY"

# Short in-process cache so summary/sector/missing endpoints share one scan.
_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {"at": 0.0, "payload": None}
_CACHE_TTL_SEC = 120.0

FIELD_KEYS = (
    "revenue",
    "ebitda",
    "ebit",
    "pat",
    "eps",
    "assets",
    "equity",
    "debt",
    "cash",
    "cfo",
    "capex",
    "shares_outstanding",
)

_FY_RE = re.compile(r"^FY\s*(\d{2,4})", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 2) if d else 0.0


def _fy_year(label: Any) -> Optional[int]:
    """FY24 / FY2024 / 2024 → calendar end year of Indian FY (Mar)."""
    text = str(label or "").strip().upper().replace(" ", "")
    if not text:
        return None
    m = _FY_RE.match(text)
    if m:
        raw = m.group(1)
        try:
            y = int(raw)
        except ValueError:
            return None
        if y < 100:
            y = 2000 + y
        return y
    try:
        y = int(text[:4])
        if 1990 <= y <= 2100:
            return y
    except ValueError:
        pass
    return None


def _period_key(label: Any) -> Optional[str]:
    text = str(label or "").strip().upper().replace(" ", "")
    return text or None


def _has_value(row: dict[str, Any], key: str) -> bool:
    v = row.get(key)
    if v is None or v == "":
        return False
    if isinstance(v, (int, float)) and v != v:  # NaN
        return False
    return True


def _classify(annual_years: int, quarters: int) -> str:
    """Bucket coverage per Step 0 spec.

    COMPLETE_10Y — ≥8y annual and ≥40 quarters (AGIB depth band)
    GOOD         — 6–9y annual or 24–39 quarters (solid, not complete)
    PARTIAL      — 3–5y annual or 8–23 quarters
    MINIMAL      — 1–2y annual (or sparse quarters)
    EMPTY        — no statements
    """
    if annual_years <= 0 and quarters <= 0:
        return CLASS_EMPTY
    if annual_years >= 8 and quarters >= 40:
        return CLASS_COMPLETE_10Y
    if annual_years >= 6 or quarters >= 24:
        return CLASS_GOOD
    if annual_years >= 3 or quarters >= 8:
        return CLASS_PARTIAL
    if annual_years >= 1 or quarters >= 1:
        return CLASS_MINIMAL
    return CLASS_EMPTY


def _load_rows(tab: str, *, limit: int = 500000) -> list[dict[str, Any]]:
    from institutional_warehouse import store

    try:
        return list(store.all_rows(tab, limit=limit) or [])
    except Exception:
        return []


def _index_by_symbol(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        sym = str(row.get("symbol") or "").strip().upper()
        if sym:
            out[sym].append(row)
    return out


def _annual_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    years: set[int] = set()
    types: Counter[str] = Counter()
    field_present: Counter[str] = Counter()
    field_rows = 0
    for row in rows:
        y = _fy_year(row.get("fiscal_year"))
        if y:
            years.add(y)
        st = str(row.get("statement_type") or "UNKNOWN").upper()
        types[st] += 1
        field_rows += 1
        for key in FIELD_KEYS:
            if _has_value(row, key):
                field_present[key] += 1
    ordered = sorted(years)
    missing_years: list[int] = []
    if ordered:
        for y in range(ordered[0], ordered[-1] + 1):
            if y not in years:
                missing_years.append(y)
    return {
        "years": len(years),
        "earliest": ordered[0] if ordered else None,
        "latest": ordered[-1] if ordered else None,
        "year_list": ordered,
        "missing_years": missing_years,
        "statement_types": dict(types),
        "has_consolidated": types.get("CONSOLIDATED", 0) > 0,
        "has_standalone": types.get("STANDALONE", 0) > 0,
        "rows": len(rows),
        "field_present": dict(field_present),
        "field_rows": field_rows,
    }


def _quarterly_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    periods: set[str] = set()
    years: set[int] = set()
    field_present: Counter[str] = Counter()
    for row in rows:
        pk = _period_key(row.get("fiscal_period") or row.get("fiscal_year"))
        if pk:
            periods.add(pk)
        y = _fy_year(row.get("fiscal_year") or row.get("fiscal_period"))
        if y:
            years.add(y)
        for key in FIELD_KEYS:
            if _has_value(row, key):
                field_present[key] += 1
    ordered = sorted(periods)
    return {
        "quarters": len(periods),
        "earliest": ordered[0] if ordered else None,
        "latest": ordered[-1] if ordered else None,
        "period_list": ordered[-12:],  # tail sample
        "years_touched": len(years),
        "rows": len(rows),
        "field_present": dict(field_present),
        "field_rows": len(rows),
    }


def _share_stats(rows: list[dict[str, Any]], stmt_rows: list[dict[str, Any]]) -> dict[str, Any]:
    from institutional_warehouse.values import to_number

    dates: set[str] = set()
    basic = diluted = outstanding = 0
    for row in rows:
        d = str(row.get("as_of") or "")[:10]
        if d:
            dates.add(d)
        if to_number(row.get("basic_shares")):
            basic += 1
        if to_number(row.get("diluted_shares")):
            diluted += 1
        if to_number(row.get("shares_outstanding") or row.get("weighted_average_shares")):
            outstanding += 1
    # Fallback: shares on statements
    stmt_with_shares = 0
    for row in stmt_rows:
        if to_number(row.get("shares_outstanding")):
            stmt_with_shares += 1
            d = str(row.get("filing_date") or row.get("fiscal_year") or row.get("fiscal_period") or "")[:10]
            if d:
                dates.add(d)
    return {
        "periods": len(dates),
        "share_count_history_rows": len(rows),
        "with_basic": basic,
        "with_diluted": diluted,
        "with_outstanding": outstanding,
        "statement_rows_with_shares": stmt_with_shares,
        "has_share_count": bool(dates) or stmt_with_shares > 0,
    }


def clear_audit_cache() -> None:
    with _CACHE_LOCK:
        _CACHE["at"] = 0.0
        _CACHE["payload"] = None


def run_audit(*, universe_limit: int = 100000, use_cache: bool = True) -> dict[str, Any]:
    """Full read-only warehouse financial coverage audit."""
    if use_cache:
        with _CACHE_LOCK:
            age = time.monotonic() - float(_CACHE.get("at") or 0.0)
            if _CACHE.get("payload") is not None and age < _CACHE_TTL_SEC:
                return _CACHE["payload"]

    masters = _load_rows("company_master", limit=universe_limit)
    annual_all = _load_rows("financials_annual", limit=500000)
    quarterly_all = _load_rows("financials_quarterly", limit=500000)
    shares_all = _load_rows("share_count_history", limit=500000)

    annual_ix = _index_by_symbol(annual_all)
    quarterly_ix = _index_by_symbol(quarterly_all)
    shares_ix = _index_by_symbol(shares_all)

    universe = 0
    listed = 0
    active = 0
    with_isin = 0

    class_counts: Counter[str] = Counter()
    annual_hist: Counter[int] = Counter()  # years → companies
    quarterly_hist: Counter[int] = Counter()  # quarters → companies (bucketed)
    field_missing: Counter[str] = Counter()  # field → companies missing on latest annual
    field_missing_any: Counter[str] = Counter()

    ge10 = ge8 = ge5 = lt5 = no_stmt = 0
    ge40q = ge24q = lt8q = no_q = 0
    share_ok = 0

    by_sector: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "companies": 0,
            "complete_10y": 0,
            "good": 0,
            "partial": 0,
            "minimal": 0,
            "empty": 0,
            "ge10_annual": 0,
            "ge40_quarters": 0,
            "no_statements": 0,
        }
    )

    companies: list[dict[str, Any]] = []
    need_backfill: list[dict[str, Any]] = []

    for m in masters:
        sym = str(m.get("symbol") or "").strip().upper()
        if not sym:
            continue
        universe += 1
        status = str(m.get("market_status") or "").lower()
        if status in {"listed", ""} or m.get("active") in (True, 1, "1", "true", None):
            listed += 1
        if m.get("active") in (True, 1, "1", "true", None) and status != "delisted":
            active += 1
        if m.get("isin"):
            with_isin += 1

        sector = str(m.get("sector") or "Unknown")
        industry = str(m.get("industry") or m.get("industry_dna") or "Unknown")
        a_stats = _annual_stats(annual_ix.get(sym) or [])
        q_stats = _quarterly_stats(quarterly_ix.get(sym) or [])
        s_stats = _share_stats(shares_ix.get(sym) or [], (annual_ix.get(sym) or []) + (quarterly_ix.get(sym) or []))

        years = int(a_stats["years"])
        quarters = int(q_stats["quarters"])
        klass = _classify(years, quarters)
        class_counts[klass] += 1
        annual_hist[years] += 1
        # Bucket quarters for histogram readability
        if quarters == 0:
            quarterly_hist[0] += 1
        elif quarters < 8:
            quarterly_hist[4] += 1  # 1-7
        elif quarters < 24:
            quarterly_hist[16] += 1  # 8-23
        elif quarters < 40:
            quarterly_hist[32] += 1  # 24-39
        else:
            quarterly_hist[48] += 1  # 40+

        if years >= 10:
            ge10 += 1
        if years >= 8:
            ge8 += 1
        if years >= 5:
            ge5 += 1
        if 0 < years < 5:
            lt5 += 1
        if years == 0 and quarters == 0:
            no_stmt += 1
        if quarters >= 40:
            ge40q += 1
        if quarters >= 24:
            ge24q += 1
        if 0 < quarters < 8:
            lt8q += 1
        if quarters == 0:
            no_q += 1
        if s_stats["has_share_count"]:
            share_ok += 1

        # Field completeness on annual rows (company missing field if zero presence)
        a_present = a_stats.get("field_present") or {}
        a_rows = int(a_stats.get("field_rows") or 0)
        missing_fields = []
        for key in FIELD_KEYS:
            if a_rows == 0 or int(a_present.get(key) or 0) == 0:
                field_missing_any[key] += 1
                missing_fields.append(key)
            # "most recent density": if present on <50% of annual rows
            if a_rows and int(a_present.get(key) or 0) < max(1, a_rows // 2):
                field_missing[key] += 1

        sec = by_sector[sector]
        sec["companies"] += 1
        if klass == CLASS_COMPLETE_10Y:
            sec["complete_10y"] += 1
        elif klass == CLASS_GOOD:
            sec["good"] += 1
        elif klass == CLASS_PARTIAL:
            sec["partial"] += 1
        elif klass == CLASS_MINIMAL:
            sec["minimal"] += 1
        else:
            sec["empty"] += 1
        if years >= 10:
            sec["ge10_annual"] += 1
        if quarters >= 40:
            sec["ge40_quarters"] += 1
        if years == 0 and quarters == 0:
            sec["no_statements"] += 1

        row = {
            "symbol": sym,
            "company_name": m.get("company_name"),
            "isin": m.get("isin"),
            "sector": sector,
            "industry": industry,
            "classification": klass,
            "annual": {
                "earliest": a_stats["earliest"],
                "latest": a_stats["latest"],
                "years": years,
                "missing_years": a_stats["missing_years"],
                "has_consolidated": a_stats["has_consolidated"],
                "has_standalone": a_stats["has_standalone"],
                "statement_types": a_stats["statement_types"],
            },
            "quarterly": {
                "earliest": q_stats["earliest"],
                "latest": q_stats["latest"],
                "quarters": quarters,
            },
            "share_count": s_stats,
            "missing_fields": missing_fields,
            "needs_backfill": klass not in {CLASS_COMPLETE_10Y},
            "backfill_priority": {
                CLASS_EMPTY: 1,
                CLASS_MINIMAL: 2,
                CLASS_PARTIAL: 3,
                CLASS_GOOD: 4,
                CLASS_COMPLETE_10Y: 5,
            }.get(klass, 3),
        }
        companies.append(row)
        if row["needs_backfill"]:
            need_backfill.append(row)

    need_backfill.sort(key=lambda r: (r["backfill_priority"], r["annual"]["years"], r["quarterly"]["quarters"]))

    # Annual histogram as sorted list
    annual_histogram = [
        {"years": y, "companies": annual_hist[y]}
        for y in sorted(annual_hist.keys())
    ]
    quarterly_histogram = [
        {
            "bucket": (
                "0" if k == 0 else
                "1–7" if k == 4 else
                "8–23" if k == 16 else
                "24–39" if k == 32 else
                "40+"
            ),
            "companies": quarterly_hist[k],
        }
        for k in (0, 4, 16, 32, 48)
        if quarterly_hist.get(k)
    ]

    sector_rows = []
    for sec, c in sorted(by_sector.items(), key=lambda kv: -kv[1]["companies"]):
        n = max(c["companies"], 1)
        sector_rows.append({
            "sector": sec,
            **c,
            "complete_10y_pct": _pct(c["complete_10y"], n),
            "partial_or_worse_pct": _pct(
                c["partial"] + c["minimal"] + c["empty"], n
            ),
            "empty_pct": _pct(c["empty"], n),
            "ge10_annual_pct": _pct(c["ge10_annual"], n),
            "ge40_quarters_pct": _pct(c["ge40_quarters"], n),
        })

    missing_fields_ranked = [
        {
            "field": key,
            "companies_missing_entirely": int(field_missing_any.get(key) or 0),
            "companies_sparse": int(field_missing.get(key) or 0),
            "missing_entirely_pct": _pct(int(field_missing_any.get(key) or 0), universe),
        }
        for key in sorted(FIELD_KEYS, key=lambda k: -int(field_missing_any.get(k) or 0))
    ]

    summary = {
        "universe": universe,
        "listed": listed,
        "active": active,
        "isin_coverage": with_isin,
        "isin_pct": _pct(with_isin, universe),
        "annual": {
            "companies_with_any": universe - sum(1 for c in companies if c["annual"]["years"] == 0),
            "ge10_years": ge10,
            "ge10_pct": _pct(ge10, universe),
            "ge8_years": ge8,
            "ge8_pct": _pct(ge8, universe),
            "ge5_years": ge5,
            "ge5_pct": _pct(ge5, universe),
            "lt5_years": lt5,
            "lt5_pct": _pct(lt5, universe),
            "none": sum(1 for c in companies if c["annual"]["years"] == 0),
            "none_pct": _pct(sum(1 for c in companies if c["annual"]["years"] == 0), universe),
            "total_rows": len(annual_all),
        },
        "quarterly": {
            "companies_with_any": universe - no_q,
            "ge40_quarters": ge40q,
            "ge40_pct": _pct(ge40q, universe),
            "ge24_quarters": ge24q,
            "ge24_pct": _pct(ge24q, universe),
            "lt8_quarters": lt8q,
            "none": no_q,
            "none_pct": _pct(no_q, universe),
            "total_rows": len(quarterly_all),
        },
        "share_count": {
            "companies_with_any": share_ok,
            "pct": _pct(share_ok, universe),
            "share_count_history_rows": len(shares_all),
        },
        "classification": {
            CLASS_COMPLETE_10Y: class_counts.get(CLASS_COMPLETE_10Y, 0),
            CLASS_GOOD: class_counts.get(CLASS_GOOD, 0),
            CLASS_PARTIAL: class_counts.get(CLASS_PARTIAL, 0),
            CLASS_MINIMAL: class_counts.get(CLASS_MINIMAL, 0),
            CLASS_EMPTY: class_counts.get(CLASS_EMPTY, 0),
        },
        "classification_pct": {
            k: _pct(class_counts.get(k, 0), universe)
            for k in (CLASS_COMPLETE_10Y, CLASS_GOOD, CLASS_PARTIAL, CLASS_MINIMAL, CLASS_EMPTY)
        },
        "no_statements": no_stmt,
        "no_statements_pct": _pct(no_stmt, universe),
        "need_backfill": len(need_backfill),
        "need_backfill_pct": _pct(len(need_backfill), universe),
        "bottleneck": (
            "annual"
            if _pct(ge10, universe) < _pct(ge40q, universe)
            else "quarterly"
            if _pct(ge40q, universe) < _pct(ge10, universe)
            else "balanced"
        ),
    }

    result = {
        "ok": True,
        "phase": "7.4F-step0",
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "read_only": True,
        "modifies_data": False,
        "summary": summary,
        "annual_histogram": annual_histogram,
        "quarterly_histogram": quarterly_histogram,
        "missing_fields": missing_fields_ranked,
        "by_sector": sector_rows,
        "companies_requiring_import": [
            {
                "symbol": r["symbol"],
                "company_name": r["company_name"],
                "sector": r["sector"],
                "classification": r["classification"],
                "annual_years": r["annual"]["years"],
                "annual_earliest": r["annual"]["earliest"],
                "annual_latest": r["annual"]["latest"],
                "quarters": r["quarterly"]["quarters"],
                "has_share_count": r["share_count"]["has_share_count"],
                "missing_fields": r["missing_fields"][:8],
            }
            for r in need_backfill[:500]
        ],
        "companies_complete_sample": [
            {
                "symbol": r["symbol"],
                "company_name": r["company_name"],
                "sector": r["sector"],
                "annual_years": r["annual"]["years"],
                "quarters": r["quarterly"]["quarters"],
            }
            for r in companies
            if r["classification"] == CLASS_COMPLETE_10Y
        ][:50],
        "plain_english": (
            f"Universe {universe}. "
            f"≥10y annual: {ge10} ({_pct(ge10, universe)}%). "
            f"≥8y annual: {ge8} ({_pct(ge8, universe)}%). "
            f"≥40 quarters: {ge40q} ({_pct(ge40q, universe)}%). "
            f"No statements: {no_stmt} ({_pct(no_stmt, universe)}%). "
            f"Need backfill (not COMPLETE_10Y): {len(need_backfill)} ({_pct(len(need_backfill), universe)}%). "
            f"Bottleneck: {summary['bottleneck']}."
        ),
        "checked_at": _now(),
        # Full company table omitted from default payload — use company endpoint / limit param.
        "_company_count": len(companies),
    }

    if use_cache:
        with _CACHE_LOCK:
            _CACHE["at"] = time.monotonic()
            _CACHE["payload"] = result
    return result


def audit_summary() -> dict[str, Any]:
    full = run_audit()
    return {
        "ok": True,
        "phase": "7.4F-step0",
        "read_only": True,
        "summary": full.get("summary"),
        "plain_english": full.get("plain_english"),
        "annual_histogram": full.get("annual_histogram"),
        "quarterly_histogram": full.get("quarterly_histogram"),
        "missing_fields": full.get("missing_fields"),
        "classification": (full.get("summary") or {}).get("classification"),
        "checked_at": full.get("checked_at"),
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def audit_sector() -> dict[str, Any]:
    full = run_audit()
    return {
        "ok": True,
        "phase": "7.4F-step0",
        "read_only": True,
        "rows": full.get("by_sector") or [],
        "summary": {
            "universe": (full.get("summary") or {}).get("universe"),
            "ge10_pct": (full.get("summary") or {}).get("annual", {}).get("ge10_pct"),
            "ge40_pct": (full.get("summary") or {}).get("quarterly", {}).get("ge40_pct"),
        },
        "plain_english": full.get("plain_english"),
        "checked_at": full.get("checked_at"),
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def missing_financials(*, limit: int = 500, classification: Optional[str] = None) -> dict[str, Any]:
    full = run_audit()
    rows = list(full.get("companies_requiring_import") or [])
    # Full need_backfill list is capped at 500 in run_audit payload; rebuild from cache
    # is enough for admin. Callers wanting more get up to that cap.
    if classification:
        rows = [r for r in rows if r.get("classification") == classification.upper()]
    return {
        "ok": True,
        "phase": "7.4F-step0",
        "read_only": True,
        "count": int((full.get("summary") or {}).get("need_backfill") or len(rows)),
        "rows": rows[: max(1, min(int(limit), 5000))],
        "missing_fields": full.get("missing_fields"),
        "summary": full.get("summary"),
        "checked_at": full.get("checked_at"),
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }


def company_audit(symbol: str) -> dict[str, Any]:
    """Detailed read-only audit for one symbol."""
    from institutional_warehouse import store

    ticker = str(symbol or "").strip().upper()
    masters = []
    try:
        masters = store.fetch("company_master", filters={"symbol": ticker}, limit=1).get("rows") or []
    except Exception:
        masters = [
            m for m in _load_rows("company_master", limit=100000)
            if str(m.get("symbol") or "").upper() == ticker
        ]
    master = masters[0] if masters else {"symbol": ticker}
    try:
        a_rows = store.all_rows("financials_annual", entity=ticker, limit=500) or []
        q_rows = store.all_rows("financials_quarterly", entity=ticker, limit=500) or []
        s_rows = store.all_rows("share_count_history", entity=ticker, limit=500) or []
    except Exception:
        a_rows = []
        q_rows = []
        s_rows = []
    a_stats = _annual_stats(a_rows)
    q_stats = _quarterly_stats(q_rows)
    s_stats = _share_stats(s_rows, a_rows + q_rows)
    years = int(a_stats["years"])
    quarters = int(q_stats["quarters"])
    klass = _classify(years, quarters)
    missing_fields = [
        k for k in FIELD_KEYS
        if int((a_stats.get("field_present") or {}).get(k) or 0) == 0
    ]
    return {
        "ok": True,
        "phase": "7.4F-step0",
        "read_only": True,
        "symbol": ticker,
        "company_name": master.get("company_name"),
        "isin": master.get("isin"),
        "sector": master.get("sector"),
        "industry": master.get("industry"),
        "classification": klass,
        "annual": a_stats,
        "quarterly": q_stats,
        "share_count": s_stats,
        "missing_fields": missing_fields,
        "needs_backfill": klass != CLASS_COMPLETE_10Y,
        "agib_standard": {
            "annual_10y": years >= 10,
            "quarters_40": quarters >= 40,
            "share_count": bool(s_stats.get("has_share_count")),
            "met": years >= 10 and quarters >= 40 and bool(s_stats.get("has_share_count")),
        },
        "checked_at": _now(),
        "programme": PROGRAMME_CODE,
        "version": PROGRAMME_VERSION,
    }
