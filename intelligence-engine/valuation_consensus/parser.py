"""Parse Capital IQ Excel/CSV into normalized valuation_consensus rows.

Spreadsheet is an import source only — never the live datastore.
"""

from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import Any

from valuation_consensus.schema import empty_row, map_header, normalize_header

_PLACEHOLDER = {"-", "--", "n/a", "na", "n.a.", "none", "nil", "null", "#n/a"}
_EXCHANGE_PREFIX = re.compile(r"^(nsei?|bse)\s*:\s*", re.I)
_BSE_CODE_RE = re.compile(r"^bse\s*:\s*([A-Z0-9]{1,15})$", re.I)
_NSE_CODE_RE = re.compile(r"^nsei?\s*:\s*([A-Z0-9.&-]{1,20})$", re.I)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    try:
        import pandas as pd

        if pd.isna(value):
            return True
    except Exception:
        pass
    s = str(value).strip()
    return (not s) or s.lower() in _PLACEHOLDER


def _to_number(value: Any) -> float | int | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip().replace(",", "").replace("%", "")
    try:
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        try:
            return float(s)
        except Exception:
            return None


def _to_text(value: Any) -> str | None:
    if _is_blank(value):
        return None
    return str(value).strip()


def decode_content(content_base64: str | bytes | None, content_bytes: bytes | None = None) -> bytes:
    if content_bytes is not None:
        return content_bytes
    if content_base64 is None:
        raise ValueError("missing_content")
    if isinstance(content_base64, bytes):
        raw = content_base64
    else:
        raw = base64.b64decode(str(content_base64))
    return raw


def read_dataframe(
    content_bytes: bytes,
    filename: str,
    *,
    sheet_name: Any = 0,
    column_names: list[str] | None = None,
):
    import pandas as pd

    ext = Path(filename or "").suffix.lower()
    header = None if column_names else 0
    if ext in {".xlsx", ".xls", ".xlsm"}:
        df = pd.read_excel(io.BytesIO(content_bytes), sheet_name=sheet_name, header=header)
    elif ext == ".csv":
        df = pd.read_csv(io.BytesIO(content_bytes), header=header)
    else:
        raise ValueError(f"unsupported_file_type:{ext or 'unknown'}")
    if isinstance(df, dict):
        df = next(iter(df.values()))
    if column_names:
        if len(column_names) != df.shape[1]:
            raise ValueError(
                f"column_count_mismatch: file has {df.shape[1]} columns, "
                f"column_names has {len(column_names)}"
            )
        df.columns = column_names
    return df.where(df.notnull(), None)


_PAREN_NSEI_RE = re.compile(r"\b(?:nsei?|bse)\s*:\s*([A-Z0-9.&-]{1,20})\b", re.I)


def _ticker_from_parent(parent_raw: Any) -> str | None:
    """Pull NSEI:/BSE: symbol embedded in CapIQ parent strings."""
    if _is_blank(parent_raw):
        return None
    m = _PAREN_NSEI_RE.search(str(parent_raw))
    if not m:
        return None
    sym = m.group(1).upper().replace(".", "").replace("&", "")
    return sym or None


def _name_key(name_raw: Any) -> str | None:
    """Stable synthetic key when no exchange ticker can be resolved."""
    if _is_blank(name_raw):
        return None
    try:
        from institutional_knowledge_tables.bulk_sheet import normalize_company_name

        norm = normalize_company_name(name_raw)
    except Exception:
        norm = re.sub(r"[^a-z0-9]+", " ", str(name_raw).lower()).strip()
    if not norm:
        return None
    slug = re.sub(r"[^A-Z0-9]+", "", norm.upper())[:24]
    return f"NAME{slug}" if slug else None


def resolve_ticker(
    ticker_raw: Any,
    name_raw: Any,
    *,
    parent_raw: Any = None,
    allow_name_key: bool = True,
) -> tuple[str | None, str]:
    """Resolve CapIQ ticker. Prefer trading_universe; fall back to exchange codes."""
    bse_code = None
    nse_symbol = None
    if not _is_blank(ticker_raw):
        raw = str(ticker_raw).strip()
        m_bse = _BSE_CODE_RE.match(raw)
        if m_bse:
            bse_code = m_bse.group(1).upper()
        m_nse = _NSE_CODE_RE.match(raw)
        if m_nse:
            nse_symbol = m_nse.group(1).upper().replace(".", "").replace("&", "")
        try:
            from trading_universe.loader import get_symbol

            t = _EXCHANGE_PREFIX.sub("", raw).upper()
            t = t.replace(".NS", "").replace(".BO", "")
            if get_symbol(t):
                return t, "exact_ticker"
            if nse_symbol and get_symbol(nse_symbol):
                return nse_symbol, "nse_universe"
        except Exception:
            t = _EXCHANGE_PREFIX.sub("", raw).upper().replace(".NS", "").replace(".BO", "")
            if t and not t.isdigit():
                return t, "raw_ticker"

    if not _is_blank(name_raw):
        try:
            from institutional_knowledge_tables.bulk_sheet import resolve_ticker as ikt_resolve

            ticker, how = ikt_resolve(ticker_raw, name_raw)
            if ticker:
                return ticker, how
        except Exception:
            pass

    parent_sym = _ticker_from_parent(parent_raw)
    if parent_sym:
        try:
            from trading_universe.loader import get_symbol

            if get_symbol(parent_sym):
                return parent_sym, "parent_nsei"
        except Exception:
            pass
        if not parent_sym.isdigit():
            return parent_sym, "parent_nsei_fallback"

    if nse_symbol:
        return nse_symbol, "nse_ticker_fallback"
    if bse_code:
        return f"BSE{bse_code}", "bse_code_fallback"
    if not _is_blank(ticker_raw):
        t = _EXCHANGE_PREFIX.sub("", str(ticker_raw).strip()).upper()
        t = t.replace(".NS", "").replace(".BO", "")
        if t and not t.isdigit():
            return t, "raw_ticker"
    if allow_name_key:
        key = _name_key(name_raw)
        if key:
            return key, "name_key"
    return None, "unresolved"


def detect_columns(columns: list[Any]) -> dict[str, Any]:
    mapped: dict[str, str] = {}  # original header -> canonical
    unmapped: list[str] = []
    ticker_col = None
    name_col = None
    for col in columns:
        field = map_header(col)
        norm = normalize_header(col)
        if field:
            mapped[str(col)] = field
            if field == "ticker" and ticker_col is None:
                ticker_col = col
            if field == "company_name" and name_col is None:
                name_col = col
        elif norm:
            unmapped.append(str(col))
        if ticker_col is None and norm in {"ticker", "symbol", "nse symbol"}:
            ticker_col = col
            mapped[str(col)] = "ticker"
        if name_col is None and norm in {"company name", "company", "name"}:
            name_col = col
            mapped[str(col)] = "company_name"
    return {
        "mapped": mapped,
        "unmapped": unmapped,
        "ticker_col": ticker_col,
        "name_col": name_col,
    }


_RETURN_FIELDS = (
    "return_ytd",
    "return_1d",
    "return_1w",
    "return_1m",
    "return_3m",
    "return_6m",
    "return_9m",
    "return_1y",
    "return_3y",
    "return_5y",
)

_NUMERIC_FIELDS = frozenset(
    {
        "cmp",
        "market_cap",
        "enterprise_value",
        "revenue",
        "ebitda",
        "target_price",
        "target_high",
        "target_low",
        "target_std_dev",
        "upside",
        "buy_count",
        "outperform_count",
        "hold_count",
        "sell_count",
        "no_opinion_count",
        "coverage",
        "avg_volume",
        *_RETURN_FIELDS,
    }
)


def _compute_upside(row: dict[str, Any]) -> float | None:
    if row.get("upside") is not None:
        return _to_number(row.get("upside"))
    cmp_v = _to_number(row.get("cmp"))
    tgt = _to_number(row.get("target_price"))
    if cmp_v and tgt and cmp_v != 0:
        return round(((tgt - cmp_v) / cmp_v) * 100.0, 4)
    return None


def parse_sheet(
    content_bytes: bytes,
    filename: str,
    *,
    sheet_name: Any = 0,
    column_names: list[str] | None = None,
) -> dict[str, Any]:
    try:
        df = read_dataframe(
            content_bytes, filename, sheet_name=sheet_name, column_names=column_names
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    detected = detect_columns(list(df.columns))
    mapped = detected["mapped"]
    ticker_col, name_col = detected["ticker_col"], detected["name_col"]
    if ticker_col is None and name_col is None:
        return {
            "ok": False,
            "error": "no_ticker_or_company_name_column",
            "columns_seen": [str(c) for c in df.columns],
            "unmapped": detected["unmapped"],
        }

    rows: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    resolve_stats: dict[str, int] = {}

    # Locate parent column for NSEI: fallback extraction
    parent_col = next(
        (c for c, f in mapped.items() if f == "parent"),
        None,
    )

    for idx, series in df.iterrows():
        ticker_raw = series.get(ticker_col) if ticker_col is not None else None
        name_raw = series.get(name_col) if name_col is not None else None
        parent_raw = series.get(parent_col) if parent_col is not None else None
        ticker, how = resolve_ticker(ticker_raw, name_raw, parent_raw=parent_raw)
        resolve_stats[how] = resolve_stats.get(how, 0) + 1
        if not ticker:
            unresolved.append(
                {
                    "row": int(idx) + 2,
                    "ticker_raw": _to_text(ticker_raw),
                    "company_name": _to_text(name_raw),
                    "reason": how,
                }
            )
            continue

        row = empty_row(ticker)
        extras: dict[str, Any] = {}
        for col in df.columns:
            val = series.get(col)
            if _is_blank(val):
                continue
            field = mapped.get(str(col))
            if not field:
                extras[str(col)] = _to_text(val) if not isinstance(val, (int, float)) else val
                continue
            if field == "ticker":
                continue
            if field in _NUMERIC_FIELDS:
                row[field] = _to_number(val)
            else:
                row[field] = _to_text(val)

        # CapIQ often emits 0 for missing target/upside — keep counts at 0, null prices.
        if row.get("coverage") in (0, 0.0) and row.get("target_price") in (0, 0.0):
            for k in ("target_price", "target_high", "target_low", "target_std_dev", "upside"):
                if row.get(k) in (0, 0.0):
                    row[k] = None

        row["upside"] = _compute_upside(row) if row.get("upside") is None else row.get("upside")
        if row.get("upside") in (0, 0.0) and row.get("target_price") is None:
            row["upside"] = None
        returns = {k: row.get(k) for k in _RETURN_FIELDS if row.get(k) is not None}
        row["returns"] = returns
        if extras:
            row["extras"] = extras
        # Prefer richer duplicate (same ticker twice in sheet → last wins with merge)
        if ticker in rows:
            prev = rows[ticker]
            for k, v in row.items():
                if k in {"extras", "returns"}:
                    continue
                if v is not None:
                    prev[k] = v
            prev_extras = dict(prev.get("extras") or {})
            prev_extras.update(row.get("extras") or {})
            prev["extras"] = prev_extras
            prev["returns"] = {**(prev.get("returns") or {}), **(row.get("returns") or {})}
            prev["upside"] = _compute_upside(prev)
            rows[ticker] = prev
        else:
            rows[ticker] = row

    return {
        "ok": True,
        "filename": filename,
        "row_count": len(rows),
        "unresolved_count": len(unresolved),
        "unresolved": unresolved[:100],
        "columns_mapped": sorted(set(mapped.values())),
        "columns_unmapped": detected["unmapped"],
        "resolve_stats": resolve_stats,
        "rows": rows,
    }


def diff_against_live(
    new_rows: dict[str, dict[str, Any]],
    live_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    skip = {"updated_at", "version_id", "source_file"}
    old_keys = set(live_rows or {})
    new_keys = set(new_rows or {})
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed: list[dict[str, Any]] = []
    for t in sorted(old_keys & new_keys):
        a = {k: v for k, v in (live_rows.get(t) or {}).items() if k not in skip}
        b = {k: v for k, v in (new_rows.get(t) or {}).items() if k not in skip}
        if a != b:
            fields = []
            for k in sorted(set(a) | set(b)):
                if a.get(k) != b.get(k):
                    fields.append({"field": k, "from": a.get(k), "to": b.get(k)})
            changed.append({"ticker": t, "fields": fields[:40]})
    return {
        "rows_added": len(added),
        "rows_removed": len(removed),
        "rows_changed": len(changed),
        "added": added[:200],
        "removed": removed[:200],
        "changed": changed[:200],
    }
