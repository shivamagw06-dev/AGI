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
OPEN_MARKET_MODES = {"market purchase", "market sale", "open market"}

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


def _date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:11].strip(), fmt).date()
        except ValueError:
            continue
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
    out: list[dict[str, Any]] = []
    for row in raw:
        clean = {str(k).strip(): v for k, v in row.items() if k}
        company = str(_pick(clean, _COLUMNS["symbol"]) or "").strip()
        person = str(_pick(clean, _COLUMNS["person"]) or "").strip()
        when = _date(_pick(clean, _COLUMNS["reported_on"]))
        action = str(_pick(clean, _COLUMNS["action"]) or "").strip()
        quantity = _number(_pick(clean, _COLUMNS["quantity"]))
        mode = str(_pick(clean, _COLUMNS["mode"]) or "").strip()
        # Every part of the key must be present or the row cannot be stored
        # without silently merging into an unrelated filing.
        if not (company and person and when and action and quantity is not None and mode):
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

    rows = sorted(merged.values(), key=lambda r: (r["reported_on"], r["company_name"]))
    dates = [r["reported_on"] for r in rows]
    return {
        "ok": bool(rows),
        "source": SOURCE,
        "files": per_file,
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
