"""Bulk company-info sheet ingest (Excel/CSV → IKT facts).

Drop a spreadsheet with one row per company and columns like
"Company Name", "Ticker", "Sector", "CEO", "PE", "Market Cap"... Each
recognized column is written as a versioned IKT fact, keyed to the
ticker resolved from the uploaded universe registry — never a
hardcoded company list, never a fabricated ticker match.
"""

from __future__ import annotations

import io
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from institutional_knowledge_tables.schema import TABLE_DEFS
from institutional_knowledge_tables.store import upsert_fact

# normalized header -> (table, field)
_COLUMN_MAP: dict[str, tuple[str, str]] = {
    "company name": ("company_master", "company_name"),
    "company": ("company_master", "company_name"),
    "name": ("company_master", "company_name"),
    "ticker": ("company_master", "ticker"),
    "symbol": ("company_master", "ticker"),
    "nse symbol": ("company_master", "ticker"),
    "nse code": ("company_master", "ticker"),
    "stock symbol": ("company_master", "ticker"),
    "isin": ("company_master", "isin"),
    "isin code": ("company_master", "isin"),
    "sector": ("company_master", "sector"),
    "industry": ("company_master", "industry"),
    "exchange": ("company_master", "exchange"),
    "website": ("company_master", "website"),
    "web site": ("company_master", "website"),
    "cin": ("company_master", "cin"),
    "country": ("company_master", "country"),
    "status": ("company_master", "status"),
    "fiscal year end": ("company_master", "fiscal_year_end"),
    "fye": ("company_master", "fiscal_year_end"),
    "ceo": ("management", "ceo"),
    "chief executive officer": ("management", "ceo"),
    "cfo": ("management", "cfo"),
    "chief financial officer": ("management", "cfo"),
    "auditor": ("management", "auditor"),
    "board": ("management", "board"),
    "independent directors": ("management", "independent_directors"),
    "market cap": ("market_data", "market_cap"),
    "marketcap": ("market_data", "market_cap"),
    "market capitalization": ("market_data", "market_cap"),
    "pe": ("valuation", "pe"),
    "p/e": ("valuation", "pe"),
    "pe ratio": ("valuation", "pe"),
    "pb": ("valuation", "pb"),
    "p/b": ("valuation", "pb"),
    "ev/ebitda": ("valuation", "ev_ebitda"),
    "ev ebitda": ("valuation", "ev_ebitda"),
    "ev/sales": ("valuation", "ev_sales"),
    "dividend yield": ("valuation", "dividend_yield"),
    "fcf yield": ("valuation", "fcf_yield"),
    "peg": ("valuation", "peg"),
    "business segments": ("business_model", "business_segments"),
    "segments": ("business_model", "business_segments"),
    "revenue mix": ("business_model", "revenue_mix"),
    "products": ("business_model", "products"),
    "services": ("business_model", "services"),
    "customers": ("business_model", "customers"),
    "geography": ("business_model", "geography"),
    "competitive position": ("business_model", "competitive_position"),
    "credit rating": ("credit_ratings", "rating"),
    "rating": ("credit_ratings", "rating"),
    "rating agency": ("credit_ratings", "agency"),
    "outlook": ("credit_ratings", "outlook"),
    # Capital IQ / screener-style exports (verbose headers, snapshot pulls)
    "primary sector": ("company_master", "sector"),
    "primary industry": ("company_master", "industry"),
    "trading status": ("company_master", "status"),
    "exchange country/region": ("company_master", "country"),
    "product name": ("products", "product"),
    "product description": ("products", "product_description"),
    "competitors": ("competitors", "peer"),
    "long business description": ("business_model", "description"),
    "business description": ("business_model", "description_short"),
    "equity currency": ("company_master", "currency"),
    "company type": ("company_master", "company_type"),
    "native language company name": ("company_master", "native_name"),
    "ultimate corporate parent": ("company_master", "parent_company"),
    "excel trading item id": ("company_master", "external_id"),
    "number of investment research documents last 30 days": ("company_master", "research_coverage_count"),
    "current and pending investors": ("business_model", "investors"),
    "industry classifications": ("business_model", "industry_classifications"),
    "of total investments / subsidiaries": ("business_model", "subsidiaries_count"),
}

# Prefix-matched (regex) for headers whose suffix varies by export settings,
# e.g. "EBITDA [LTM] ($USDmm, Historical rate)" or "Market Capitalization
# [My Setting] [Latest] ($USDmm, Historical rate)". Evaluated only when an
# exact _COLUMN_MAP lookup misses.
_PREFIX_PATTERNS: tuple[tuple[re.Pattern[str], str, str, str], ...] = (
    (re.compile(r"^day close price"), "market_data", "close", "latest"),
    (re.compile(r"^daily volume"), "market_data", "volume", "latest"),
    (re.compile(r"^total enterprise value"), "market_data", "enterprise_value", "latest"),
    (re.compile(r"^market capitalization"), "market_data", "market_cap", "latest"),
    (re.compile(r"^ebitda\b"), "financial_statements", "ebitda", "LTM"),
    (re.compile(r"^total revenue\b"), "financial_statements", "revenue", "LTM"),
    # Capital IQ / screener-style exports: headers with a variable embedded
    # date/suffix ("% Price Change [YTD as of 1/1/2026]", "Index Constituents
    # (All Equity Listings)") — matched by prefix so the exact date/suffix
    # text doesn't need to be hardcoded. All "% Price Change [...]" windows
    # are point-in-time snapshot facts from the same export pull, so — like
    # close/volume/market_cap/enterprise_value above — they are all keyed to
    # period="latest" rather than the upload date, so a single
    # get_table(..., period="latest") call returns the whole snapshot.
    (re.compile(r"^price change ytd"), "market_data", "returns_ytd", "latest"),
    (re.compile(r"^price change 1 day"), "market_data", "returns_1d", "latest"),
    (re.compile(r"^price change 1 week"), "market_data", "returns_1w", "latest"),
    (re.compile(r"^price change 1 month"), "market_data", "returns_1m", "latest"),
    (re.compile(r"^price change 3 months"), "market_data", "returns_3m", "latest"),
    (re.compile(r"^price change 6 months"), "market_data", "returns_6m", "latest"),
    (re.compile(r"^price change 9 months"), "market_data", "returns_9m", "latest"),
    (re.compile(r"^price change 1 year"), "market_data", "returns_1y", "latest"),
    (re.compile(r"^price change 3 years"), "market_data", "returns_3y", "latest"),
    (re.compile(r"^price change 5 years"), "market_data", "returns_5y", "latest"),
    (re.compile(r"^index constituents"), "business_model", "index_constituents", "latest"),
    (re.compile(r"^next announced earnings date"), "market_data", "next_earnings_date_announced", "latest"),
    (re.compile(r"^next expected earnings date"), "market_data", "next_earnings_date_expected", "latest"),
)

_TICKER_HEADERS = {"ticker", "symbol", "nse symbol", "nse code", "stock symbol"}
_NAME_HEADERS = {"company name", "company", "name"}
_PERIOD_HEADERS = {"as of", "date", "period", "quarter", "fy", "as of date"}


def _norm(header: Any) -> str:
    h = str(header or "").strip().lower().replace("_", " ")
    h = re.sub(r"[^a-z0-9/ ]", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def _today() -> str:
    return date.today().isoformat()


def _to_python(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


_PLACEHOLDER_VALUES = {"-", "--", "n/a", "na", "n.a.", "none", "nil", "null", "#n/a"}


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
    if s == "":
        return True
    # Capital IQ / screener exports use a bare "-" (and similar tokens) as
    # their "no data available" placeholder — treat it as blank so it is
    # never stored as if it were a real fact value.
    return s.lower() in _PLACEHOLDER_VALUES


def read_sheet_rows(
    content_bytes: bytes,
    filename: str,
    *,
    sheet_name: Any = 0,
    column_names: list[str] | None = None,
) -> Any:
    """Return a pandas DataFrame for .xlsx/.xls/.csv content.

    Some export tools (e.g. Capital IQ "continuation" batches) omit the
    header row on subsequent files from the same saved screen. Pass the
    header list from the first file as `column_names` to reuse it — the
    file is then read with no header row and those names applied positionally.
    """
    import pandas as pd

    ext = Path(filename or "").suffix.lower()
    header = None if column_names else 0
    if ext in {".xlsx", ".xls", ".xlsm"}:
        df = pd.read_excel(io.BytesIO(content_bytes), sheet_name=sheet_name, header=header)
    elif ext == ".csv":
        df = pd.read_csv(io.BytesIO(content_bytes), header=header)
    else:
        raise ValueError(f"unsupported_file_type:{ext or 'unknown'} (use .xlsx, .xls, or .csv)")
    if isinstance(df, dict):  # sheet_name=None returns {sheet: df}
        df = next(iter(df.values()))
    if column_names:
        if len(column_names) != df.shape[1]:
            raise ValueError(
                f"column_count_mismatch: file has {df.shape[1]} columns, "
                f"column_names has {len(column_names)}"
            )
        df.columns = column_names
    return df.where(df.notnull(), None)


_LEGAL_SUFFIXES = re.compile(
    r"\b(limited|ltd|pvt|private|corporation|corp|inc|plc|llp)\b",
    re.I,
)
_LEADING_ARTICLE = re.compile(r"^the\s+", re.I)
# CapIQ uses both "NSE:" and "NSEI:" (National Stock Exchange of India)
# as exchange prefixes on ticker columns — treat them equivalently.
_EXCHANGE_PREFIX = re.compile(r"^(nsei?|bse)\s*:\s*", re.I)


_JOINER_WORD = re.compile(r"\band\b", re.I)


def normalize_company_name(name: Any) -> str:
    """Strip legal suffixes, articles, initials-punctuation, and '&'/'and'
    so 'L.G. Balakrishnan & Bros Ltd' and 'Oil and Natural Gas Corporation
    Limited' compare equal to their catalog forms. Matching-only, never stored.
    """
    n = str(name or "").strip().lower()
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")  # Nestlé -> Nestle
    n = n.replace(".", "")  # "L.G." -> "lg" (no inserted space, unlike other punctuation)
    # Drop apostrophes entirely rather than treating them as word separators:
    # "TCS's" must normalize to "tcs", not "tcs s" — that stray one-letter "s"
    # remnant would otherwise falsely word-overlap-match any company whose
    # name contains a literal "S" token (e.g. "S&S Power Switchgear Limited"
    # -> "s s power switchgear"). Strip a trailing possessive "'s" as a unit
    # first so "TCS's" -> "tcs", not "tcss".
    n = n.replace("\u2019", "'")
    n = re.sub(r"'s\b", "", n)
    n = n.replace("'", "")
    n = _LEGAL_SUFFIXES.sub(" ", n)
    n = n.replace("&", " ")
    n = _JOINER_WORD.sub(" ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = _LEADING_ARTICLE.sub("", n)
    return re.sub(r"\s+", " ", n).strip()


def _normalized_universe_index() -> list[tuple[str, str, str]]:
    """(normalized_name, symbol, raw_name) for every row in the uploaded
    trading universe — comparison is normalized on both sides so legal
    suffixes/punctuation differences ('Dr. Reddy's' vs 'Dr Reddys') don't
    block a real match.
    """
    from trading_universe.loader import load_rows

    return [(normalize_company_name(r["name"]), r["symbol"], r["name"]) for r in load_rows()]


# CapIQ BSE identifiers are usually numeric ("BSE:500191") but a few
# older/SME names carry an alphabetic BSE symbol ("BSE:PRESSMN"). Both
# are explicit source-supplied identifiers — accept either.
_BSE_CODE_RE = re.compile(r"^bse\s*:\s*([A-Z0-9]{1,15})$", re.I)
_NSE_CODE_RE = re.compile(r"^nsei?\s*:\s*([A-Z0-9.&-]{1,20})$", re.I)


def resolve_ticker(ticker_raw: Any, name_raw: Any) -> tuple[str | None, str]:
    """Resolve a row to a real ticker. Never invents one.

    Tries the NSE-anchored uploaded universe (trading_universe) first. If a
    company is not in that universe, and the source row itself carries an
    explicit exchange-qualified identifier — BSE numeric/alpha code
    ("BSE:500191", "BSE:PRESSMN") or NSEI/NSE ticker ("NSEI:AAKAAR") —
    that identifier becomes the canonical ticker. This is not inventing
    an identifier: it is the identifier the uploaded source data itself
    provides, distinct from a chat question where no ticker was ever
    supplied by the user.
    """
    from trading_universe.loader import get_symbol

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
        t = _EXCHANGE_PREFIX.sub("", raw).upper()
        t = t.replace(".NS", "").replace(".BO", "")
        if get_symbol(t):
            return t, "exact_ticker"
    if not _is_blank(name_raw):
        norm_query = normalize_company_name(name_raw)
        if norm_query:
            index = _normalized_universe_index()
            exact = [(sym, raw) for norm, sym, raw in index if norm == norm_query]
            if exact:
                if len(exact) == 1:
                    return exact[0][0], "exact_name_match"
                # Two+ universe rows share this exact normalized name — most
                # often two share classes (equity + DVR) of the same legal
                # entity. Guessing "top1" would silently bind the row to
                # whichever happens to sort first; safer to fall through to
                # the exchange-code fallback (a distinct, explicit identifier)
                # or unresolved than to invent a pick between two real tickers.
                pass
            # NOTE: a word-subset/substring "fuzzy" fallback was tried here
            # and removed. Audited against the full ~2,027-row Capital IQ
            # corpus, it fired for 17 rows and produced a *wrong* company for
            # 11 of them (e.g. "Reliance Infrastructure Limited" bound to
            # RIIL — actually "Reliance Industrial Infrastructure Limited";
            # "Shree Digvijay Cement Company Limited" bound to SHREECEM —
            # actually "Shree Cement Limited"). A >60% wrong-match rate is
            # incompatible with this store's zero-substitution contract, so
            # only exact-ticker, exact-normalized-name, and explicit
            # exchange-qualified identifiers are trusted. Unmatched names
            # fall through to the exchange-code fallbacks below, or
            # unresolved — never a guess.
    if bse_code:
        # No universe listing found for this company — fall back to the BSE
        # code the source row itself supplied, rather than dropping a real,
        # named, actively-traded company purely because it isn't in the
        # NSE-anchored universe.
        return f"BSE{bse_code}", "bse_code_fallback"
    if nse_symbol:
        # CapIQ marks many SME/small-cap NSE listings as "NSEI:<SYMBOL>"
        # that are not in the (Nifty-anchored) trading_universe upload.
        # The symbol itself is the real NSE ticker the source provided —
        # keep it as-is (no "NSE" prefix; bare NSE tickers are the
        # platform's existing convention for universe-listed names).
        return nse_symbol, "nse_ticker_fallback"
    return None, "unresolved"


def _detect_columns(columns: list[Any]) -> dict[str, Any]:
    header_by_norm: dict[str, Any] = {}
    mapped: dict[str, tuple[str, str]] = {}
    period_override: dict[str, str] = {}
    unmapped: list[str] = []
    ticker_col = None
    name_col = None
    period_col = None
    for col in columns:
        norm = _norm(col)
        if not norm:
            continue
        header_by_norm[norm] = col
        if norm in _TICKER_HEADERS and ticker_col is None:
            ticker_col = col
        if norm in _NAME_HEADERS and name_col is None:
            name_col = col
        if norm in _PERIOD_HEADERS and period_col is None:
            period_col = col
        if norm in _COLUMN_MAP:
            mapped[norm] = _COLUMN_MAP[norm]
            continue
        prefix_hit = next((p for p in _PREFIX_PATTERNS if p[0].search(norm)), None)
        if prefix_hit:
            _, table, field, period_label = prefix_hit
            mapped[norm] = (table, field)
            period_override[norm] = period_label
        else:
            unmapped.append(str(col))
    return {
        "header_by_norm": header_by_norm,
        "mapped": mapped,
        "period_override": period_override,
        "unmapped": unmapped,
        "ticker_col": ticker_col,
        "name_col": name_col,
        "period_col": period_col,
    }


def _prefer_canonical_ticker(existing: str, candidate: str) -> str:
    """When the same legal company name resolves to two tickers across
    CapIQ chunks (e.g. HMT Limited as both BSE:500191 and NSEI:HMT), keep
    one. Prefer a real NSE/universe ticker over a synthetic BSE* key —
    bare NSE symbols are the platform's existing convention.
    """
    if existing == candidate:
        return existing
    existing_bse = existing.startswith("BSE")
    candidate_bse = candidate.startswith("BSE")
    if existing_bse and not candidate_bse:
        return candidate
    if candidate_bse and not existing_bse:
        return existing
    # Same class — keep the first one we saw (stable, never flip-flops).
    return existing


def ingest_company_sheet(
    content_bytes: bytes,
    filename: str,
    *,
    sheet_name: Any = 0,
    dry_run: bool = False,
    source_label: str | None = None,
    column_names: list[str] | None = None,
    name_canonical: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Parse a company-info spreadsheet and write recognized columns as
    versioned IKT facts. Rows whose company can't be resolved against the
    uploaded universe registry are reported, never guessed.

    `column_names`: pass the header list from a sibling file when this file
    is a headerless continuation batch of the same export (same column
    order, header only on the first chunk).

    `name_canonical`: optional shared `{normalized_company_name: ticker}`
    map across multi-file seeds. When the same legal name appears under
    two exchange identifiers (BSE code vs NSEI symbol), facts are written
    to a single preferred ticker instead of splitting one company across
    two IKT keys. The seed owns and threads this dict across files.
    """
    try:
        df = read_sheet_rows(content_bytes, filename, sheet_name=sheet_name, column_names=column_names)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    detected = _detect_columns(list(df.columns))
    mapped, unmapped = detected["mapped"], detected["unmapped"]
    period_override = detected["period_override"]
    ticker_col, name_col, period_col = (
        detected["ticker_col"],
        detected["name_col"],
        detected["period_col"],
    )
    header_by_norm = detected["header_by_norm"]

    if ticker_col is None and name_col is None:
        return {
            "ok": False,
            "error": "no_ticker_or_company_name_column",
            "hint": "Include a 'Ticker'/'Symbol' or 'Company Name' column so rows can be resolved.",
            "columns_seen": [str(c) for c in df.columns],
        }

    source = source_label or f"bulk_upload:{filename}"
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    fields_written_total = 0
    tables_touched: set[str] = set()
    if name_canonical is None:
        name_canonical = {}
    superseded: list[dict[str, str]] = []

    for idx, row in df.iterrows():
        ticker_raw = row.get(ticker_col) if ticker_col is not None else None
        name_raw = row.get(name_col) if name_col is not None else None
        ticker, method = resolve_ticker(ticker_raw, name_raw)
        if not ticker:
            unresolved.append(
                {
                    "row": int(idx) + 2,  # +2 ≈ human spreadsheet row (header + 1-index)
                    "company_name": _to_python(name_raw),
                    "ticker_raw": _to_python(ticker_raw),
                    "reason": method,
                }
            )
            continue

        # Dedup by legal name across exchange identifiers.
        norm_name = normalize_company_name(name_raw) if not _is_blank(name_raw) else ""
        if norm_name:
            existing = name_canonical.get(norm_name)
            if existing:
                preferred = _prefer_canonical_ticker(existing, ticker)
                if preferred != ticker:
                    method = "name_dedup_reuse"
                    ticker = preferred
                elif preferred != existing:
                    # Upgrading BSE* → NSE: drop the orphan BSE key so the
                    # company_router name index can't keep pointing at it.
                    superseded.append({"from": existing, "to": preferred, "name": norm_name})
                    if not dry_run:
                        try:
                            from institutional_knowledge_tables.store import delete_company

                            delete_company(existing)
                        except Exception:
                            pass
                    name_canonical[norm_name] = preferred
                    ticker = preferred
                    method = f"{method}+name_dedup_upgrade"
                else:
                    name_canonical[norm_name] = ticker
            else:
                name_canonical[norm_name] = ticker

        period_val = row.get(period_col) if period_col is not None else None
        row_period = str(period_val) if not _is_blank(period_val) else None
        written_fields: list[str] = []
        for norm, (table, field) in mapped.items():
            if table == "company_master" and field == "ticker":
                # Always the resolved, canonical ticker — never the raw sheet
                # cell (which may be an exchange-prefixed code like
                # "BSE:500002" that would contradict the entity key itself).
                value = ticker
            else:
                raw_val = row.get(header_by_norm[norm])
                if _is_blank(raw_val):
                    continue
                value = _to_python(raw_val)
            if not dry_run:
                kwargs: dict[str, Any] = {"source": source, "trigger": "bulk_sheet_upload"}
                if TABLE_DEFS[table]["keyed_by_period"]:
                    # Priority: an explicit per-row period column > a
                    # column-specific label (e.g. "LTM", "latest" inferred
                    # from the header itself) > today's upload date.
                    kwargs["period"] = row_period or period_override.get(norm) or _today()
                upsert_fact(ticker, table, field, value, **kwargs)
            written_fields.append(f"{table}.{field}")
            tables_touched.add(table)
            fields_written_total += 1
        resolved.append(
            {
                "row": int(idx) + 2,
                "ticker": ticker,
                "method": method,
                "fields_written": written_fields,
            }
        )

    return {
        "ok": True,
        "dry_run": dry_run,
        "filename": filename,
        "source": source,
        "total_rows": int(len(df)),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "unresolved_rows": unresolved[:50],
        "resolved_sample": resolved[:20],
        "superseded_count": len(superseded),
        "superseded_sample": superseded[:20],
        "mapped_columns": {header_by_norm[n]: f"{t}.{f}" for n, (t, f) in mapped.items()},
        "unmapped_columns": unmapped,
        "tables_touched": sorted(tables_touched),
        "fields_written_total": fields_written_total,
        "ticker_column": str(ticker_col) if ticker_col is not None else None,
        "name_column": str(name_col) if name_col is not None else None,
        "period_column": str(period_col) if period_col is not None else None,
    }
