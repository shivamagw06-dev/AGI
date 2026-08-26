"""Load Trendlyne insider and SAST disclosure exports.

The Insider Activity page currently asks a live service for this data and gets
refused - HTTP 429, zero rows - so the page renders empty. These exports carry
the same information, cost nothing per request, and are richer than what the
page was using: they separate who traded (promoter, promoter group, designated
person, relative) from how (market purchase, gift, off-market transfer).

That distinction is the point. A promoter buying on the open market and a
director receiving a gift of shares are both "acquisitions", and treating them
as one number turns a signal into noise. 70 of the 178 rows in the first file
were market purchases; 11 were gifts.

Several exports overlap, because the vendor caps a download at 1,000 rows and a
wide date range silently returns only the newest ones. A request for six months
came back with 997 rows in August and 3 in June. So every file in the folder is
read and the rows are deduplicated on the trade itself rather than trusting any
one file to be complete.
"""

from __future__ import annotations

import csv
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Optional

SOURCE = "trendlyne_insider_export"
REPO_ROOT = Path(__file__).resolve().parents[2]
# Any file whose name mentions insider trading, in either format.
FILE_PATTERN = re.compile(r"insider", re.IGNORECASE)

# Only these put the person's own money at risk at a market price. A gift or an
# off-market transfer moves shares without a market transaction, and an ESOP
# allotment is compensation.
# SAST filings write a bare "Market" where an insider filing writes "Market
# Purchase" - 198 rows, every one of them a market transaction. Leaving it out
# excluded a quarter of the real open-market activity from the page.
OPEN_MARKET_MODES = {"market purchase", "market sale", "open market", "market"}

# An insider filing is a director or promoter trading their own company under
# the PIT regulations. A SAST filing is an acquirer crossing a shareholding
# threshold under the takeover code - a market transaction, but not an insider
# one, and never reported with a price. Splitting them explains what otherwise
# looks like missing data: value is present on 95% of insider filings and 0% of
# SAST ones.
def regime(regulation: Any) -> str:
    return "sast" if "sast" in str(regulation or "").lower() else "insider"


# The vendor writes "None" or "-" in action and mode when the filing did not
# state one - a pledge revocation has no buy/sell mode, and some acquisitions
# arrive without a mode at all. The warehouse reads both of those as absent, and
# both columns are part of the key, so 48 real disclosures were rejected.
#
# They are stored under an explicit placeholder instead. It says the same thing
# the file says - the filing named no mode - while keeping the key complete so
# the row survives and re-imports match it rather than duplicating it. It is not
# treated as an open-market trade, because an unstated mode is not evidence of
# one.
UNSPECIFIED = "unspecified"
_NULL_TEXT = {"", "-", "--", "n/a", "na", "nan", "none", "null"}


def _stated(value: Any) -> str:
    """The value as written, or the placeholder when the filing stated none."""
    return _present(value) or UNSPECIFIED


def _present(value: Any) -> str:
    """The value as written, or empty when the file wrote a word for nothing.

    Used for the fields that identify the filing - the company and the person.
    A placeholder is wrong for these: a trade attributed to "None" belongs to
    nobody, and the warehouse would reject it as blank anyway. Such a row is
    dropped rather than stored under a name that means nothing.
    """
    text = str(value or "").strip()
    return "" if text.lower() in _NULL_TEXT else text

_COLUMNS = {
    "symbol": ("Stock",),
    "person": ("Client Name",),
    "category": ("Client Category",),
    "action": ("Action*", "Action"),
    "reported_on": ("Reported To/By Exchange", "Reported"),
    "quantity": ("Quantity",),
    "post_holding": ("Post Transaction Holding",),
    "traded_pct": ("Traded %",),
    "avg_price": ("Avg. Price", "Avg Price"),
    "value": ("Value",),
    "period": ("Period",),
    "regulation": ("Regulation (Insider/SAST)", "Regulation"),
    "security_type": ("Security Type",),
    "mode": ("Mode",),
}


def _number(value: Any) -> Optional[float]:
    """Indian exports carry thousands separators and '-' for absent."""
    text = str(value or "").strip().replace(",", "")
    if not text or text in {"-", "--", "NA", "N/A"}:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return out if out == out else None


# Every shape these exports have arrived in. Two-digit years are last so a
# four-digit year is never truncated into one: "24/08/2026" must not be read as
# 24 August 2020 by a %y pattern matching the first two digits.
_DATE_FORMATS = (
    "%Y-%m-%d",      # 2026-08-24, and the date half of an Excel datetime
    "%d-%b-%Y",      # 24-Aug-2026
    "%d %b %Y",      # 24 Aug 2026
    "%d/%m/%Y",      # 24/08/2026
    "%d-%m-%Y",      # 24-08-2026
    "%d/%m/%y",      # 24/08/26  - the NSE web export's default
    "%d-%m-%y",      # 24-08-26
)


def _date(value: Any) -> Optional[date]:
    """A reported date, or nothing.

    The web export writes 24/08/26 while the file download writes a full
    datetime, and a pasted day without a usable date is dropped as unstorable -
    so an unhandled format silently empties the entire paste. That is exactly
    what happened: every row of a 36-row paste was rejected because the year
    had two digits.

    Slicing to 11 characters trims Excel's " 00:00:00" without cutting any of
    the formats above, all of which are 10 characters or fewer.
    """
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text[:11].strip()
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
        # A two-digit year lands in 20xx. These filings are current, and a
        # 1926 reported date would be stored happily and be wrong forever.
        if parsed.year < 100:
            parsed = parsed.replace(year=parsed.year + 2000)
        return parsed
    return None


def _pick(row: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _read_csv(path: Path) -> list[dict[str, Any]]:
    # utf-8-sig strips the byte-order mark the export writes.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_xlsx(path: Path) -> list[dict[str, Any]]:
    """The workbook carries a title line above the header row."""
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.worksheets[0]
        header: Optional[list[str]] = None
        out: list[dict[str, Any]] = []
        for raw in sheet.iter_rows(values_only=True):
            values = ["" if c is None else str(c).strip() for c in raw]
            if header is None:
                # The header is the first row that names the stock column.
                if any(v == "Stock" for v in values):
                    header = values
                continue
            if not any(values):
                continue
            out.append(dict(zip(header, values)))
        return out
    finally:
        workbook.close()


def parse_file(path: Path) -> list[dict[str, Any]]:
    raw = _read_xlsx(path) if path.suffix.lower() in {".xlsx", ".xlsm"} else _read_csv(path)
    return normalise_rows(raw)


def normalise_rows(raw: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Header-keyed rows to storable trades.

    Split out of parse_file so a pasted block and an exported file are held to
    the same rules. A paste that skipped this would accept rows the file
    importer rejects, and the difference would only show up as bad data later.
    """
    out: list[dict[str, Any]] = []
    for row in raw:
        clean = {str(k).strip(): v for k, v in row.items() if k}
        company = _present(_pick(clean, _COLUMNS["symbol"]))
        person = _present(_pick(clean, _COLUMNS["person"]))
        when = _date(_pick(clean, _COLUMNS["reported_on"]))
        action = _stated(_pick(clean, _COLUMNS["action"]))
        quantity = _number(_pick(clean, _COLUMNS["quantity"]))
        mode = _stated(_pick(clean, _COLUMNS["mode"]))
        # Who filed, against which company, on what day, for how many shares.
        # Without any one of these the row cannot be stored without silently
        # merging into an unrelated filing. Action and mode are not on this
        # list: they carry a placeholder when unstated, so they are never blank.
        if not (company and person and when and quantity is not None):
            continue
        out.append({
            "company_name": company,
            "reported_on": when.isoformat(),
            "person": person,
            "category": str(_pick(clean, _COLUMNS["category"]) or "").strip() or None,
            "action": action,
            "quantity": quantity,
            "mode": mode,
            "value": _number(_pick(clean, _COLUMNS["value"])),
            "avg_price": _number(_pick(clean, _COLUMNS["avg_price"])),
            "traded_pct": _number(_pick(clean, _COLUMNS["traded_pct"])),
            "post_holding": _number(_pick(clean, _COLUMNS["post_holding"])),
            "regulation": str(_pick(clean, _COLUMNS["regulation"]) or "").strip() or None,
            "regime": regime(_pick(clean, _COLUMNS["regulation"])),
            "security_type": str(_pick(clean, _COLUMNS["security_type"]) or "").strip() or None,
            "period": str(_pick(clean, _COLUMNS["period"]) or "").strip() or None,
            "is_open_market": "true" if mode.lower() in OPEN_MARKET_MODES else "false",
            "source": SOURCE,
        })
    return out


def discover(root: Path = REPO_ROOT) -> list[Path]:
    """Every insider export in the folder, oldest name first."""
    found = [p for p in root.glob("*")
             if p.is_file() and p.suffix.lower() in {".csv", ".xlsx", ".xlsm"}
             and FILE_PATTERN.search(p.name)]
    return sorted(found, key=lambda p: p.name)


_SUFFIXES = re.compile(
    r"\b(ltd|limited|the|company|co|corp|corporation|pvt|private|inc)\b")


def _normalise_name(value: Any) -> str:
    text = re.sub(r"[^a-z0-9 ]", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", _SUFFIXES.sub(" ", text)).strip()


def symbol_index() -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Company name to ticker, from company_master.

    Two lookups: an exact normalised name, and a list for prefix matching.
    The export writes short trade names - "Shaily Engineering" against a master
    entry of "Shaily Engineering Plastics Limited" - so exact matching alone
    resolves only a quarter of them.
    """
    try:
        from institutional_warehouse import store
    except Exception:
        return {}, []
    exact: dict[str, str] = {}
    listed: list[tuple[str, str]] = []
    try:
        rows = store.all_rows("company_master", limit=20000) or []
    except Exception:
        return {}, []
    for row in rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        for field in ("company_name", "legal_name"):
            name = _normalise_name(row.get(field))
            if name:
                exact.setdefault(name, symbol)
                listed.append((name, symbol))
    return exact, listed


def resolve_symbol(company: str, index: tuple[dict[str, str], list[tuple[str, str]]]
                   ) -> tuple[Optional[str], str]:
    """Ticker for a company name, and how it was found.

    An ambiguous prefix returns nothing. Two companies sharing an opening word
    would otherwise attach a disclosure to whichever happened to sort first,
    and a trade filed against the wrong company is worse than one with no
    ticker at all.
    """
    exact, listed = index
    name = _normalise_name(company)
    if not name:
        return None, "blank"
    if name in exact:
        return exact[name], "exact"
    candidates = {sym for master, sym in listed if master.startswith(name + " ")}
    if len(candidates) == 1:
        return candidates.pop(), "prefix"
    if candidates:
        return None, "ambiguous"
    return None, "unmatched"


def _fingerprint(row: dict[str, Any]) -> tuple:
    return (row["company_name"], row["reported_on"], row["person"],
            row["action"], row["quantity"], row["mode"])


def _trade(row: dict[str, Any]) -> tuple:
    """The filing itself, ignoring how the exports described it."""
    return (row["company_name"], row["reported_on"], row["person"],
            row["quantity"])


def _collapse_unspecified(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop a row whose action or mode is unstated when a stated one exists.

    Four filings arrive twice: one export names the mode ("Off Market") and
    another leaves the column empty for the same company, person, day and
    quantity. Because mode is part of the key, both survive deduplication and
    the trade is counted twice - inflating the volume the page reports.

    They are the same filing, and the stated version is strictly more
    informative, so the unstated copy is dropped. This only applies where a
    stated row exists; an unstated filing with no counterpart is kept, because
    the alternative is losing a real disclosure.
    """
    rows = list(rows)
    stated: set[tuple] = {
        _trade(r) for r in rows
        if r["mode"] != UNSPECIFIED and r["action"] != UNSPECIFIED
    }
    return [r for r in rows
            if _trade(r) not in stated
            or (r["mode"] != UNSPECIFIED and r["action"] != UNSPECIFIED)]


def parse(root: Path = REPO_ROOT) -> dict[str, Any]:
    """Read every export and collapse the overlap between them."""
    files = discover(root)
    if not files:
        return {"ok": False, "error": "no_insider_exports_found", "rows": []}

    merged: dict[tuple, dict[str, Any]] = {}
    per_file: list[dict[str, Any]] = []
    for path in files:
        try:
            rows = parse_file(path)
        except Exception as exc:
            per_file.append({"file": path.name, "error": str(exc)[:160], "rows": 0})
            continue
        before = len(merged)
        for row in rows:
            merged[_fingerprint(row)] = row
        per_file.append({"file": path.name, "rows": len(rows),
                         "new": len(merged) - before,
                         "duplicate": len(rows) - (len(merged) - before)})

    return {**finalise(merged), "files": per_file}


def finalise(merged: dict[tuple, dict[str, Any]]) -> dict[str, Any]:
    """Resolve tickers, collapse the overlap, and report what came out."""
    # Attach tickers where the master knows the company. Roughly two thirds do
    # not resolve - the export covers small companies outside our universe -
    # and those keep a blank symbol rather than a fabricated one.
    index = symbol_index()
    match_counts: dict[str, int] = {}
    for row in merged.values():
        symbol, how = resolve_symbol(row["company_name"], index)
        row["symbol"] = symbol
        row["symbol_match"] = how
        match_counts[how] = match_counts.get(how, 0) + 1

    rows = sorted(_collapse_unspecified(merged.values()),
                  key=lambda r: (r["reported_on"], r["company_name"]))
    dates = [r["reported_on"] for r in rows]
    return {
        "ok": bool(rows),
        "source": SOURCE,
        "rows": rows,
        "row_count": len(rows),
        "companies": len({r["company_name"] for r in rows}),
        "first_reported": min(dates) if dates else None,
        "last_reported": max(dates) if dates else None,
        "open_market_rows": sum(1 for r in rows if r["is_open_market"] == "true"),
        "symbol_match": match_counts,
        "with_symbol": sum(1 for r in rows if r.get("symbol")),
        "limitations": [
            "The vendor caps a download at 1,000 rows and returns the newest "
            "ones without warning, so a wide date range looks complete and is "
            "not. Coverage is only as good as the files supplied.",
            "The export names companies by trade name and covers a wider "
            "universe than company_master. Only about a third resolve to a "
            "ticker; the rest are stored with a blank symbol and cannot be "
            "joined to prices until the master covers them.",
        ],
    }


def import_trades(*, actor: str = "fwcp", root: Path = REPO_ROOT) -> dict[str, Any]:
    from institutional_warehouse import gateway

    parsed = parse(root)
    if not parsed.get("ok"):
        return parsed
    written = gateway.write("insider_trades", parsed["rows"], source=SOURCE,
                            actor=actor, reason="trendlyne_insider_export")
    return {**{k: v for k, v in parsed.items() if k != "rows"},
            "written": written, "ok": bool(written.get("ok"))}

# --------------------------------------------------------------------------
# Pasted input
#
# The exports are downloaded by hand and land in the repo, which means a day's
# disclosures only reach the warehouse when someone remembers to commit and
# deploy. Pasting straight from the spreadsheet skips that, and goes through
# exactly the same normalisation so the two routes cannot drift apart.
# --------------------------------------------------------------------------


def _delimiter(header: str) -> str:
    """Excel and Sheets both copy as tab-separated; a saved CSV is not.

    Chosen from the header alone: a company name legitimately contains a comma
    ("Tata Motors, Ltd"), so counting commas across the whole block would pick
    the wrong split on data that is genuinely tab-separated.
    """
    if "\t" in header:
        return "\t"
    return ";" if header.count(";") > header.count(",") else ","


def parse_pasted(text: str) -> dict[str, Any]:
    """A clipboard block to the same rows a file would have produced."""
    body = (text or "").strip("\n")
    if not body.strip():
        return {"ok": False, "error": "nothing_pasted", "rows": []}

    lines = [line for line in body.splitlines() if line.strip()]
    if len(lines) < 2:
        return {"ok": False, "error": "header_row_and_at_least_one_trade_required",
                "rows": []}

    reader = csv.DictReader(lines, delimiter=_delimiter(lines[0]))
    try:
        raw = [dict(row) for row in reader]
    except csv.Error as exc:
        return {"ok": False, "error": f"unreadable:{exc}"[:160], "rows": []}

    headers = [h for h in (reader.fieldnames or []) if h]
    rows = normalise_rows(raw)
    if not rows:
        # Naming the headers we did get is the difference between a user
        # fixing their paste in ten seconds and filing a bug.
        return {"ok": False, "error": "no_usable_rows", "rows": [],
                "pasted_rows": len(raw), "headers_seen": headers,
                "headers_required": ["Stock", "Client Name",
                                     "Reported To/By Exchange", "Quantity"],
                "hint": ("Every row needs a company, a person, a reported date "
                         "and a quantity. Copy the header row too.")}

    merged = {_fingerprint(row): row for row in rows}
    out = finalise(merged)
    out["pasted_rows"] = len(raw)
    out["headers_seen"] = headers
    # Rows in, rows kept: a paste that silently loses half its lines to a
    # missing quantity should say so before anyone trusts the total.
    out["dropped_rows"] = len(raw) - len(rows)
    return out


def import_pasted(text: str, *, actor: str = "insider_paste") -> dict[str, Any]:
    """Parse a pasted block and write it. Same table, same gateway, same keys."""
    from institutional_warehouse import gateway

    parsed = parse_pasted(text)
    if not parsed.get("ok"):
        return parsed
    written = gateway.write("insider_trades", parsed["rows"], source=SOURCE,
                            actor=actor, reason="insider_paste")
    return {**{k: v for k, v in parsed.items() if k != "rows"},
            "written": written, "ok": bool(written.get("ok"))}
