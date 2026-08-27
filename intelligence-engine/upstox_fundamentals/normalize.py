"""Normalise Upstox fundamentals payloads into warehouse rows.

Unit conversion for statement aggregates happens in the warehouse gateway
(Phase 7.4B) via source default ``upstox`` → crore → INR million.
"""

from __future__ import annotations

import re
import calendar
from datetime import date, datetime, timezone
from typing import Any, Optional

from upstox_fundamentals.models import PROVIDER_VERSION, SOURCE

_PERIOD_RE = re.compile(
    r"^(?:FY)?(?P<year>\d{4})(?:[-_/]?(?:Q(?P<q>[1-4])|(?P<half>H[12])))?$",
    re.I,
)

# Upstox v2 fundamentals use calendar labels like "Mar 2026", "Dec 2025".
_MONTH_YEAR_RE = re.compile(
    r"^(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    r"[\s\-/]+(?P<year>\d{2,4})$",
    re.I,
)
_MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _num(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text.lower() in {"na", "n/a", "-", "null", "none", "--"}:
        return None
    try:
        out = float(text)
    except (TypeError, ValueError):
        return None
    return None if out != out else out


def _today() -> str:
    return date.today().isoformat()


def _iso_date(value: Any) -> Optional[str]:
    """Normalize provider dates without silently truncating human labels."""
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    month_year = _MONTH_YEAR_RE.match(text)
    if month_year:
        month = _MONTH_NUM[month_year.group("mon")[:3].lower()]
        year = int(month_year.group("year"))
        if year < 100:
            year += 2000
        return date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    return None


def _pick(data: dict[str, Any], *keys: str) -> Any:
    lower = {str(k).strip().lower().replace(" ", "_"): v for k, v in data.items()}
    for key in keys:
        if key.lower() in lower and lower[key.lower()] not in (None, ""):
            return lower[key.lower()]
    # Fuzzy contains
    for key in keys:
        token = key.lower().replace("_", "")
        for lk, lv in lower.items():
            if token in lk.replace("_", "") and lv not in (None, ""):
                return lv
    return None


def _statement_type(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    if "STAND" in text:
        return "STANDALONE"
    if "CONS" in text:
        return "CONSOLIDATED"
    return "UNKNOWN"


def _parse_month_year_period(text: str) -> dict[str, Any]:
    """Map Upstox 'Mar 2026' / 'Dec 2025' labels onto Indian FY periods.

    Indian FY ends 31 March: Apr–Mar. The year in the label is the calendar
    year of the period end; FY label uses the March-ending year.
    """
    m = _MONTH_YEAR_RE.match(text.strip())
    if not m:
        return {}
    mon = _MONTH_NUM.get(m.group("mon").lower()[:3])
    if not mon:
        return {}
    year = int(m.group("year"))
    if year < 100:
        year += 2000
    # FY end year: Jan–Mar belong to FY of that calendar year; Apr–Dec to next.
    fy_end = year if mon <= 3 else year + 1
    fy_label = f"FY{fy_end}"
    # Quarter within Indian FY
    if mon in (4, 5, 6):
        q = "Q1"
    elif mon in (7, 8, 9):
        q = "Q2"
    elif mon in (10, 11, 12):
        q = "Q3"
    else:  # Jan–Mar
        q = "Q4"
    return {
        "fiscal_year": fy_label,
        "quarter": q,
        "fiscal_period": f"{fy_label}{q}",
        # Default quarterly; yearly endpoint overrides to ANNUAL in normalise_statements.
        "frequency": "QUARTERLY",
        "period_end_month": mon,
        "period_end_year": year,
    }


def _parse_period(label: str) -> dict[str, Any]:
    text = str(label or "").strip()
    month_year = _parse_month_year_period(text)
    if month_year:
        return month_year
    m = _PERIOD_RE.match(text.replace(" ", ""))
    if not m:
        # Try FY2024-25 / Mar-24 style leftovers
        years = re.findall(r"20\d{2}", text)
        q = re.search(r"Q([1-4])", text, re.I)
        if years:
            year = years[0]
            if q:
                return {
                    "fiscal_year": f"FY{year}",
                    "quarter": f"Q{q.group(1)}",
                    "fiscal_period": f"FY{year}Q{q.group(1)}",
                    "frequency": "QUARTERLY",
                }
            return {"fiscal_year": f"FY{year}", "fiscal_period": f"FY{year}", "frequency": "ANNUAL"}
        return {}
    year = m.group("year")
    q = m.group("q")
    if q:
        return {
            "fiscal_year": f"FY{year}",
            "quarter": f"Q{q}",
            "fiscal_period": f"FY{year}Q{q}",
            "frequency": "QUARTERLY",
        }
    return {"fiscal_year": f"FY{year}", "fiscal_period": f"FY{year}", "frequency": "ANNUAL"}


def _period_map(node: Any) -> dict[str, Any]:
    """Extract {period_label: value} leaves from nested Upstox statement trees."""
    out: dict[str, Any] = {}
    if not isinstance(node, dict):
        return out
    keys = list(node.keys())
    periodish = [k for k in keys if _parse_period(str(k)) or re.search(r"20\d{2}", str(k))]
    if periodish and len(periodish) >= max(1, len(keys) // 2):
        for k in periodish:
            out[str(k)] = node[k]
        return out
    for value in node.values():
        if isinstance(value, dict):
            nested = _period_map(value)
            for pk, pv in nested.items():
                out.setdefault(pk, pv)
    return out


def _history_to_values(history: Any) -> dict[str, Any]:
    """Convert Upstox history arrays [{period, value}] into {period: value}."""
    out: dict[str, Any] = {}
    if not isinstance(history, list):
        return out
    for point in history:
        if not isinstance(point, dict):
            continue
        period = point.get("period") or point.get("label") or point.get("fiscal_period")
        if period is None:
            continue
        out[str(period)] = point.get("value")
    return out


def _extract_history_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull category/particular history blocks from Upstox v2 fundamentals."""
    items: list[dict[str, Any]] = []
    # Summary categories: income_statement / cash_flow arrays
    for key in ("income_statement", "cash_flow", "balance_sheet"):
        block = data.get(key)
        if not isinstance(block, list):
            continue
        for row in block:
            if not isinstance(row, dict):
                continue
            name = row.get("category") or row.get("particular") or row.get("name")
            values = _history_to_values(row.get("history"))
            if name and values:
                items.append({"name": str(name), "values": values})
    # Detailed line items when fs=true
    full = data.get("full_statement")
    if isinstance(full, list):
        for row in full:
            if not isinstance(row, dict):
                continue
            name = row.get("particular") or row.get("category") or row.get("name")
            values = _history_to_values(row.get("history"))
            if name and values:
                items.append({"name": str(name), "values": values})
    # Some balance-sheet payloads use a top-level history of metric objects
    top_hist = data.get("history")
    if isinstance(top_hist, list):
        for row in top_hist:
            if not isinstance(row, dict):
                continue
            name = row.get("particular") or row.get("category") or row.get("name") or row.get("metric")
            if row.get("history"):
                values = _history_to_values(row.get("history"))
            else:
                # Flat {period: value} metric row
                values = {
                    str(k): v for k, v in row.items()
                    if k not in {"particular", "category", "name", "metric", "change"}
                    and _parse_period(str(k))
                }
            if name and values:
                items.append({"name": str(name), "values": values})
    return items


def _line_items(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map canonical field → {period: value} from an Upstox statement payload."""
    data = payload.get("data") if isinstance(payload.get("data"), (dict, list)) else payload
    units_in = None
    statement_type = "UNKNOWN"
    if isinstance(data, dict):
        units_in = data.get("units_in") or data.get("unit")
        # Prefer explicit statement type — never treat time_period (yearly/quarterly) as type.
        statement_type = _statement_type(
            data.get("statement_type") or data.get("type")
        )
        root = data.get("financials") or data.get("statements") or data.get("data") or data
    else:
        root = data

    # Flatten list of line-item objects.
    items: list[dict[str, Any]] = []
    if isinstance(data, dict):
        items.extend(_extract_history_items(data))
    if isinstance(root, list) and not items:
        items = [x for x in root if isinstance(x, dict)]
    elif isinstance(root, dict):
        # Either keyed by line name or nested sections.
        for key, value in root.items():
            if key in {
                "units_in", "unit", "time_period", "statement_type", "type", "status",
                "income_statement", "cash_flow", "balance_sheet", "full_statement", "history",
            }:
                continue
            if isinstance(value, dict) and _period_map(value):
                items.append({"name": key, "values": _period_map(value)})
            elif isinstance(value, (int, float, str)):
                continue
            elif isinstance(value, dict):
                for nested_key, nested_val in value.items():
                    if isinstance(nested_val, dict) and _period_map(nested_val):
                        items.append({"name": nested_key, "values": _period_map(nested_val)})
                    elif isinstance(nested_val, dict):
                        pm = _period_map(nested_val)
                        if pm:
                            items.append({"name": nested_key, "values": pm})

    # Longer / more specific aliases first — avoid "cash" matching "operating_cash_flow".
    field_aliases = (
        ("cfo", ("operating_cash_flow", "cash_from_operations", "cash_flow_from_operations", "cfo")),
        ("cfi", ("investing_cash_flow", "cash_from_investing", "cash_flow_from_investing", "cfi")),
        ("cff", ("financing_cash_flow", "cash_from_financing", "cash_flow_from_financing", "cff")),
        ("free_cash_flow", ("free_cash_flow", "fcf")),
        ("capex", ("capital_expenditure", "purchase_of_fixed_assets", "capex")),
        ("operating_revenue", ("operating_revenue",)),
        ("gross_profit", ("gross_profit",)),
        ("ebitda", ("ebitda",)),
        ("ebit", ("operating_profit", "operating_income_ebit", "operating_income", "ebit")),
        ("pat", ("profit_after_tax", "net_profit", "net_income", "pat")),
        ("pbt", ("profit_before_tax", "pbt")),
        ("finance_cost", ("finance_cost", "interest_expense", "interest")),
        ("tax", ("tax_expense", "tax")),
        ("eps", ("earnings_per_share", "basic_eps", "eps_-_basic", "eps_basic", "eps")),
        ("revenue", ("total_revenue", "total_income", "net_sales", "revenue", "sales")),
        ("current_assets", ("current_assets",)),
        ("current_liabilities", ("current_liabilities",)),
        ("working_capital", ("working_capital",)),
        ("shares_outstanding", ("shares_outstanding", "share_capital_shares", "no_of_shares")),
        ("assets", ("total_assets", "assets")),
        ("equity", ("shareholders_equity", "total_equity", "net_worth", "equity")),
        ("debt", ("total_debt", "borrowings", "debt")),
        ("cash", ("cash_and_equivalents", "cash_equivalents", "cash")),
    )

    def _match_field(lname: str) -> Optional[str]:
        # Exact alias match wins; otherwise longest alias contained in the name.
        best = None
        best_len = -1
        for field, aliases in field_aliases:
            for alias in aliases:
                if lname == alias:
                    return field
                if len(alias) >= 4 and alias in lname and len(alias) > best_len:
                    best = field
                    best_len = len(alias)
        return best

    # Build period → field map
    by_period: dict[str, dict[str, Any]] = {}
    for item in items:
        name = str(item.get("name") or item.get("particular") or item.get("line") or "").strip()
        values = item.get("values")
        if not isinstance(values, dict):
            values = _period_map(item)
        if not name or not values:
            continue
        lname = name.lower().replace(" ", "_")
        canon = _match_field(lname)
        if not canon:
            continue
        for period, raw in values.items():
            bucket = by_period.setdefault(str(period), {})
            if canon not in bucket or bucket[canon] is None:
                bucket[canon] = _num(raw)

    return {
        "by_period": by_period,
        "units_in": units_in,
        "statement_type": statement_type,
    }


def _dqiv_statement(row: dict[str, Any]) -> tuple[str, str, float]:
    notes: list[str] = []
    assets = _num(row.get("assets"))
    equity = _num(row.get("equity"))
    debt = _num(row.get("debt"))
    if assets is not None and equity is not None and debt is not None:
        rhs = equity + debt
        if rhs and abs(assets - rhs) / max(abs(assets), 1.0) > 0.15:
            notes.append("assets_ne_liabilities_equity")
    if equity is not None and equity < 0:
        notes.append("negative_equity")
    shares = _num(row.get("shares_outstanding"))
    if shares is not None and shares <= 0:
        notes.append("zero_shares")
    rev = _num(row.get("revenue"))
    if rev is not None and rev < 0:
        notes.append("negative_revenue")
    if notes:
        return "warning", ";".join(notes), 0.7
    return "passed", "", 0.9


def normalise_profile(payload: dict[str, Any]) -> dict[str, Any]:
    symbol = str(payload.get("symbol") or "").strip().upper()
    isin = str(payload.get("isin") or "").strip().upper()
    if not symbol or not isin:
        return {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        data = {}
    instrument_key = str(
        payload.get("instrument_key")
        or data.get("instrument_key")
        or f"NSE_EQ|{isin}"
    )
    company_name = str(
        _pick(data, "company_name", "name", "short_name")
        or payload.get("company_name")
        or symbol
    ).strip()
    notes: list[str] = []
    if not company_name:
        notes.append("missing_name")
    sector = _pick(data, "sector", "gics_sector")
    industry = _pick(data, "industry", "gics_industry")
    if not sector:
        notes.append("missing_sector")
    status = "warning" if notes else "passed"
    as_of = str(payload.get("as_of") or _today())
    row = {
        "company_id": str(payload.get("company_id") or symbol),
        "symbol": symbol,
        "isin": isin,
        "instrument_key": instrument_key,
        "company_name": company_name,
        "legal_name": _pick(data, "legal_name", "full_name", "company_name") or company_name,
        "sector": sector,
        "industry": industry,
        "sub_industry": _pick(data, "sub_industry", "gics_sub_industry", "industry_group"),
        "business_description": _pick(
            data, "business_description", "description", "about", "company_description",
            "company_profile",
        ),
        "market_cap_inr": _num(_pick(data, "market_cap_inr", "market_cap", "mcap")),
        "market_cap_usd": _num(_pick(data, "market_cap_usd")),
        # These provider fields describe the whole sector, not the company.
        # Keep them separate so they can never contaminate company valuation.
        "sector_market_cap_inr": _num(
            (_pick(data, "sector_market_cap_inr") or {}).get("value")
            if isinstance(_pick(data, "sector_market_cap_inr"), dict)
            else None
        ),
        "sector_market_cap_usd": _num(
            (_pick(data, "sector_market_cap_usd") or {}).get("value")
            if isinstance(_pick(data, "sector_market_cap_usd"), dict)
            else None
        ),
        "website": _pick(data, "website", "url", "web_url"),
        "city": _pick(data, "city", "headquarters_city"),
        "state": _pick(data, "state"),
        "country": _pick(data, "country") or "India",
        "listing_date": _pick(data, "listing_date", "ipo_date", "listed_date"),
        "employee_count": int(_num(_pick(data, "employee_count", "employees", "employee")) or 0) or None,
        "exchange": _pick(data, "exchange") or "NSE",
        "market_status": "listed",
        "active": True,
        "as_of": as_of,
        "confidence": 0.9 if status == "passed" else 0.7,
        "dqiv_status": status,
        "validation_notes": ";".join(notes),
        "source": SOURCE,
        "provider_version": PROVIDER_VERSION + "/profile",
    }
    return row


def normalise_statements(
    payload: dict[str, Any],
    *,
    kind: str,
) -> list[dict[str, Any]]:
    """kind: income-statement | balance-sheet | cash-flow → financials_* rows."""
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        return []
    raw = payload if isinstance(payload, dict) else {}
    data_obj = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    time_period = str(
        (data_obj or {}).get("time_period") or raw.get("time_period") or ""
    ).strip().lower()
    parsed = _line_items(raw)
    by_period = parsed["by_period"]
    stype = parsed["statement_type"]
    if stype == "UNKNOWN":
        stype = _statement_type(payload.get("statement_type"))
    rows: list[dict[str, Any]] = []
    for period, fields in by_period.items():
        meta = _parse_period(period)
        if not meta:
            continue
        if time_period == "yearly":
            fy = meta.get("fiscal_year")
            meta = {
                "fiscal_year": fy,
                "fiscal_period": fy,
                "frequency": "ANNUAL",
                "quarter": None,
            }
        elif time_period == "quarterly":
            fy = meta.get("fiscal_year")
            q = meta.get("quarter") or "Q4"
            meta = {
                "fiscal_year": fy,
                "quarter": q,
                "fiscal_period": f"{fy}{q}",
                "frequency": "QUARTERLY",
            }
        row = {
            "symbol": symbol,
            "statement_type": stype,
            "statement_frequency": meta.get("frequency") or "UNKNOWN",
            "fiscal_year": meta.get("fiscal_year"),
            "fiscal_period": meta.get("fiscal_period"),
            "quarter": meta.get("quarter"),
            "source": SOURCE,
            "units_in": parsed.get("units_in") or payload.get("units_in"),
            **fields,
        }
        # Kind-specific: keep only relevant fields but merge is fine — empty ok.
        if kind == "income-statement":
            keep = {
                "revenue", "gross_profit", "ebitda", "ebit", "pbt", "pat", "eps",
                "finance_cost",
            }
            for k in list(row.keys()):
                if k in keep or k in {
                    "symbol", "statement_type", "statement_frequency", "fiscal_year",
                    "fiscal_period", "quarter", "source", "units_in",
                }:
                    continue
                if k in {"assets", "equity", "debt", "cash", "cfo", "cfi", "cff", "capex"}:
                    row.pop(k, None)
        status, notes, conf = _dqiv_statement(row)
        row["confidence"] = conf
        row["dqiv_status"] = status
        row["validation_notes"] = notes
        rows.append(row)
    return rows


def merge_statement_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge income/balance/cash rows that share the same natural key."""
    merged: dict[tuple, dict[str, Any]] = {}
    for row in rows:
        freq = str(row.get("statement_frequency") or "").upper()
        if freq == "QUARTERLY" or row.get("quarter"):
            key = (
                row.get("symbol"),
                row.get("statement_type"),
                row.get("fiscal_period") or row.get("fiscal_year"),
                "Q",
            )
        else:
            key = (row.get("symbol"), row.get("statement_type"), row.get("fiscal_year"), "A")
        bucket = merged.setdefault(key, dict(row))
        for k, v in row.items():
            if v is not None and (bucket.get(k) is None or k in {
                "revenue", "ebitda", "ebit", "pat", "eps", "assets", "equity", "debt",
                "cash", "cfo", "cfi", "cff", "capex", "shares_outstanding",
            }):
                if bucket.get(k) is None or k == "source":
                    bucket[k] = v
                elif k in {
                    "revenue", "ebitda", "ebit", "pat", "eps", "assets", "equity", "debt",
                    "cash", "cfo", "cfi", "cff", "capex", "shares_outstanding",
                    "current_assets", "current_liabilities", "working_capital", "gross_profit",
                    "pbt",
                }:
                    bucket[k] = v
        status, notes, conf = _dqiv_statement(bucket)
        bucket["confidence"] = conf
        bucket["dqiv_status"] = status
        bucket["validation_notes"] = notes
        bucket["source"] = SOURCE
    return list(merged.values())


def normalise_shareholding(payload: dict[str, Any]) -> list[dict[str, Any]]:
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        return []
    data = payload.get("data") if payload.get("data") is not None else payload
    rows_in: list[dict[str, Any]] = []
    if isinstance(data, list):
        rows_in = [x for x in data if isinstance(x, dict)]
    elif isinstance(data, dict):
        series = data.get("holdings") or data.get("shareholdings") or data.get("history")
        if isinstance(series, list):
            rows_in = [x for x in series if isinstance(x, dict)]
        else:
            rows_in = [data]

    # Current Upstox shape is category-oriented:
    # [{category: "promoters", history: [{period, value}, ...]}, ...].
    # Pivot it into one complete ownership observation per reporting period.
    category_rows = [r for r in rows_in if r.get("category") and isinstance(r.get("history"), list)]
    if category_rows:
        by_period: dict[str, dict[str, Any]] = {}
        category_map = {
            "promoters": "promoter",
            "fii": "fii",
            "other_dii": "dii",
            "mutual_funds": "mutual_funds",
            "retail_and_other": "public",
        }
        for category_row in category_rows:
            field = category_map.get(str(category_row.get("category") or "").strip().lower())
            if not field:
                continue
            for point in category_row.get("history") or []:
                if not isinstance(point, dict) or not point.get("period"):
                    continue
                bucket = by_period.setdefault(str(point["period"]), {})
                bucket[field] = point.get("value")
        rows_in = [{"period": period, **values} for period, values in by_period.items()]

    out: list[dict[str, Any]] = []
    for item in rows_in:
        as_of = (
            _pick(item, "as_of", "date", "period", "quarter_end", "report_date")
            or payload.get("as_of")
            or _today()
        )
        promoter = _num(_pick(item, "promoter", "promoter_holding", "promoters"))
        fii = _num(_pick(item, "fii", "fpi", "foreign_institutional"))
        other_dii = _num(_pick(item, "dii", "domestic_institutional"))
        mutual_funds = _num(_pick(item, "mutual_funds", "mutual_fund"))
        dii = (other_dii or 0) + (mutual_funds or 0) if other_dii is not None or mutual_funds is not None else None
        public = _num(_pick(item, "public", "public_holding", "retail"))
        government = _num(_pick(item, "government", "govt", "government_holding"))
        others = _num(_pick(item, "others", "other", "others_holding"))
        institutional = None
        if fii is not None or dii is not None:
            institutional = (fii or 0) + (dii or 0)
        notes: list[str] = []
        parts = [x for x in (promoter, fii, dii, public, government, others) if x is not None]
        if len(parts) >= 2:
            total = sum(parts)
            if total and abs(total - 100) > 8:
                notes.append("holdings_not_near_100")
        status = "warning" if notes else "passed"
        out.append({
            "symbol": symbol,
            "as_of": _iso_date(as_of) or str(as_of),
            "promoter_holding": promoter,
            "fii": fii,
            "dii": dii,
            "institutional_holding": institutional,
            "public_holding": public,
            "government_holding": government,
            "others_holding": others,
            "confidence": 0.9 if status == "passed" else 0.7,
            "dqiv_status": status,
            "validation_notes": ";".join(notes),
            "source": SOURCE,
        })
    return out


def normalise_corporate_actions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Secondary source — lower confidence; never intended to overwrite NSE/LIDI."""
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        return []
    data = payload.get("data") if payload.get("data") is not None else payload
    events = data if isinstance(data, list) else (
        data.get("events") or data.get("corporate_actions") or []
        if isinstance(data, dict) else []
    )
    out: list[dict[str, Any]] = []
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        details = {}
        for row in ev.get("event_details") or []:
            if isinstance(row, dict) and row.get("name"):
                details[str(row["name"]).strip().lower()] = row.get("value")
        name = str(ev.get("name") or ev.get("action_type") or ev.get("type") or "").lower()
        action_type = "dividend"
        for token, kind in (
            ("split", "split"),
            ("bonus", "bonus"),
            ("rights", "rights"),
            ("buyback", "buyback"),
            ("buy back", "buyback"),
            ("merger", "merger"),
            ("demerger", "demerger"),
            ("dividend", "dividend"),
        ):
            if token in name:
                action_type = kind
                break
        action_date_raw = (
            details.get("ex dividend date")
            or details.get("ex-date")
            or details.get("ex date")
            or ev.get("expiry_date")
            or ev.get("action_date")
            or details.get("record date")
        )
        action_date = _iso_date(action_date_raw)
        announcement_date = _iso_date(details.get("announcement date"))
        if not action_date:
            continue
        out.append({
            "symbol": symbol,
            "action_date": action_date,
            "action_type": action_type,
            "dividend": _num(ev.get("amount")) if action_type == "dividend" else None,
            "split": ev.get("ratio") if action_type == "split" else None,
            "bonus": ev.get("ratio") if action_type == "bonus" else None,
            "rights": ev.get("ratio") if action_type == "rights" else None,
            "details": details.get("details") or ev.get("name"),
            "announcement_date": announcement_date,
            "effective_date": action_date,
            "confidence": 0.55,  # secondary
            "source": SOURCE,
        })
    return out


def normalise_competitors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    symbol = str(payload.get("symbol") or "").strip().upper()
    if not symbol:
        return []
    data = payload.get("data") if payload.get("data") is not None else payload
    peers_in: list[Any] = []
    if isinstance(data, list):
        peers_in = data
    elif isinstance(data, dict):
        peers_in = data.get("competitors") or data.get("peers") or data.get("data") or []
        if isinstance(peers_in, dict):
            peers_in = list(peers_in.values())

    isin_map: dict[str, str] = payload.get("isin_map") or {}
    as_of = str(payload.get("as_of") or _today())
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for peer in peers_in or []:
        if isinstance(peer, str):
            instrument_key = peer
            peer_isin = peer.split("|")[-1] if "|" in peer else ""
            peer_symbol = isin_map.get(peer_isin.upper(), "")
        elif isinstance(peer, dict):
            instrument_key = str(
                peer.get("instrument_key") or peer.get("instrumentKey") or ""
            ).strip()
            peer_isin = str(peer.get("isin") or "").strip().upper()
            if not peer_isin and "|" in instrument_key:
                peer_isin = instrument_key.split("|")[-1].upper()
            peer_symbol = str(
                peer.get("symbol") or peer.get("ticker") or isin_map.get(peer_isin, "")
            ).strip().upper()
        else:
            continue
        if not peer_symbol and peer_isin:
            peer_symbol = isin_map.get(peer_isin, peer_isin)
        if not peer_symbol:
            continue
        peer_symbol = peer_symbol.upper()
        if peer_symbol == symbol or peer_symbol in seen:
            continue
        seen.add(peer_symbol)
        out.append({
            "symbol": symbol,
            "peer_symbol": peer_symbol,
            "peer_isin": peer_isin or None,
            "peer_instrument_key": instrument_key or (f"NSE_EQ|{peer_isin}" if peer_isin else None),
            "sector": payload.get("sector"),
            "industry": payload.get("industry"),
            # Provider peers are candidates. Sector/business-model validation
            # must promote them before AGI treats them as canonical competitors.
            "relationship": "related",
            "confidence": 0.6,
            "as_of": as_of,
            "source": SOURCE,
        })
    return out
