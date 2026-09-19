"""Bulk import — Excel paste, CSV/XLSX upload, Capital IQ exports.

An import is a two-step transaction:

1. ``stage`` parses the payload, auto-maps columns, validates every row and
   stores the batch. Nothing has touched the warehouse yet.
2. ``commit`` writes the accepted rows, journals the changes and audits who did
   it. Rejected rows are never written.
"""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse import audit, db, store, validation
from institutional_warehouse.schema import Tab, tab as get_tab
from institutional_warehouse.values import now_iso

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Header spellings seen in NSE dumps, Capital IQ exports and analyst workbooks.
ALIASES: dict[str, str] = {
    "ticker": "symbol",
    "nsesymbol": "symbol",
    "nse": "symbol",
    "scrip": "symbol",
    "security": "symbol",
    "company": "symbol",
    "companyticker": "symbol",
    "bse": "bse_symbol",
    "bsecode": "bse_symbol",
    "name": "company_name",
    "companyname": "company_name",
    "tradingdate": "date",
    "timestamp": "date",
    "closeprice": "close",
    "lastprice": "close",
    "ltp": "close",
    "prevclose": "close",
    "adjclose": "adjusted_close",
    "totaltradedquantity": "volume",
    "ttq": "volume",
    "qty": "volume",
    "deliverypercentage": "delivery_pct",
    "delivery": "delivery_pct",
    "mcap": "market_cap",
    "marketcapitalisation": "market_cap",
    "marketcapitalization": "market_cap",
    "sharesoutstanding": "shares_outstanding",
    "shares": "shares_outstanding",
    "fy": "fiscal_year",
    "year": "fiscal_year",
    "period": "fiscal_period",
    "quarterlabel": "fiscal_period",
    "sales": "revenue",
    "totalrevenue": "revenue",
    "netsales": "revenue",
    "operatingprofit": "ebitda",
    "profitbeforetax": "pbt",
    "profitaftertax": "pat",
    "netprofit": "pat",
    "netincome": "pat",
    "earningspershare": "eps",
    "dilutedeps": "eps",
    "totalassets": "assets",
    "shareholdersequity": "equity",
    "networth": "equity",
    "totaldebt": "debt",
    "borrowings": "debt",
    "cashandequivalents": "cash",
    "capitalexpenditure": "capex",
    "cashfromoperations": "cfo",
    "operatingcashflow": "cfo",
    "cashfrominvesting": "cfi",
    "cashfromfinancing": "cff",
    "freecashflow": "free_cash_flow",
    "bookvaluepershare": "book_value",
    "pe": "pe",
    "peratio": "pe",
    "pricetoearnings": "pe",
    "forwardpe": "forward_pe",
    "pb": "pb",
    "pricetobook": "pb",
    "evebitda": "ev_ebitda",
    "evsales": "ev_sales",
    "pricesales": "price_sales",
    "ps": "price_sales",
    "dividendyield": "dividend_yield",
    "targetprice": "target_price",
    "pricetarget": "target_price",
    "hightarget": "high_target",
    "lowtarget": "low_target",
    "analysts": "analyst_count",
    "consensusdate": "consensus_date",
    "asof": "as_of",
    "asofdate": "as_of",
    "promoter": "promoter_holding",
    "promoters": "promoter_holding",
    "fiiholding": "fii",
    "diiholding": "dii",
    "mf": "mutual_funds",
    "public": "public_holding",
    "documenttype": "document_type",
    "doctype": "document_type",
    "themes": "management_themes",
}


def _norm(text: Any) -> str:
    return _NON_ALNUM.sub("", str(text or "").strip().lower())


def map_headers(tab: Tab, headers: Sequence[str]) -> dict[str, Any]:
    """Auto-map incoming headers onto tab columns."""
    by_key = {_norm(c.key): c.key for c in tab.columns}
    by_label = {_norm(c.label): c.key for c in tab.columns}
    mapping: dict[str, Optional[str]] = {}
    unmapped: list[str] = []
    for header in headers:
        token = _norm(header)
        target = by_key.get(token) or by_label.get(token) or ALIASES.get(token)
        if target and tab.column(target) is None:
            target = None
        mapping[str(header)] = target
        if not target:
            unmapped.append(str(header))
    return {
        "mapping": mapping,
        "unmapped": unmapped,
        "mapped_count": sum(1 for v in mapping.values() if v),
    }


def parse_delimited(text: str, *, delimiter: Optional[str] = None) -> tuple[list[str], list[list[str]]]:
    """Parse pasted Excel (TSV) or CSV content into headers + rows."""
    body = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not body:
        return [], []
    if delimiter is None:
        first = body.split("\n", 1)[0]
        delimiter = "\t" if first.count("\t") >= first.count(",") and "\t" in first else ","
    reader = csv.reader(io.StringIO(body), delimiter=delimiter)
    rows = [r for r in reader if any(str(c).strip() for c in r)]
    if not rows:
        return [], []
    return [str(c).strip() for c in rows[0]], [list(r) for r in rows[1:]]


def rows_from_matrix(
    tab: Tab,
    headers: Sequence[str],
    matrix: Iterable[Sequence[Any]],
    *,
    mapping: Optional[dict[str, Optional[str]]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    resolved = mapping or map_headers(tab, headers)["mapping"]
    out: list[dict[str, Any]] = []
    for raw in matrix:
        row: dict[str, Any] = {}
        for index, header in enumerate(headers):
            target = resolved.get(str(header))
            if not target:
                continue
            row[target] = raw[index] if index < len(raw) else None
        if any(v not in (None, "") for v in row.values()):
            out.append(row)
    return out, {"mapping": resolved}


def stage(
    tab_id: str,
    *,
    rows: Optional[Sequence[dict[str, Any]]] = None,
    text: Optional[str] = None,
    headers: Optional[Sequence[str]] = None,
    matrix: Optional[Sequence[Sequence[Any]]] = None,
    mapping: Optional[dict[str, Optional[str]]] = None,
    actor: str = "admin",
    source: str = "manual_import",
    delimiter: Optional[str] = None,
    preview: int = 25,
) -> dict[str, Any]:
    tab = get_tab(tab_id)
    detected_mapping: dict[str, Any] = {}

    if rows is None:
        if text:
            parsed_headers, parsed_matrix = parse_delimited(text, delimiter=delimiter)
        else:
            parsed_headers, parsed_matrix = list(headers or []), [list(r) for r in (matrix or [])]
        if not parsed_headers:
            return {"ok": False, "error": "no_headers"}
        detected_mapping = map_headers(tab, parsed_headers)
        resolved = mapping or detected_mapping["mapping"]
        rows, _ = rows_from_matrix(tab, parsed_headers, parsed_matrix, mapping=resolved)
        detected_mapping["mapping"] = resolved

    report = validation.validate_payload(tab.id, list(rows or []))
    import_id = uuid.uuid4().hex
    db.execute(
        "INSERT INTO wh_imports (id, created_at, tab_id, actor, source, rows_seen, rows_accepted,"
        " rows_rejected, report, committed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
        (
            import_id,
            now_iso(),
            tab.id,
            actor,
            source,
            report["seen"],
            report["accepted_count"],
            report["rejected_count"],
            json.dumps(
                {
                    "accepted": report["accepted"],
                    "rejected": report["rejected"],
                    "warnings": report["warnings"],
                    "mapping": detected_mapping,
                },
                default=str,
            ),
        ),
    )
    audit.record("import", tab_id=tab.id, actor=actor,
                 detail={"stage": "staged", "import_id": import_id,
                         "seen": report["seen"], "accepted": report["accepted_count"],
                         "rejected": report["rejected_count"]},
                 ok=report["rejected_count"] == 0)
    return {
        "ok": True,
        "import_id": import_id,
        "tab": tab.id,
        "seen": report["seen"],
        "accepted": report["accepted_count"],
        "rejected": report["rejected_count"],
        "duplicates": report["duplicates"],
        "warnings": report["warnings"][:50],
        "rejections": report["rejected"][:50],
        "mapping": detected_mapping,
        "preview": report["accepted"][: max(0, int(preview))],
        "committed": False,
    }


def get_import(import_id: str) -> Optional[dict[str, Any]]:
    rows = db.query("SELECT * FROM wh_imports WHERE id = ?", (import_id,))
    if not rows:
        return None
    row = rows[0]
    try:
        report = json.loads(row.get("report") or "{}")
    except Exception:
        report = {}
    return {**row, "report": report}


def commit(import_id: str, *, actor: str = "admin", recalculate: bool = True) -> dict[str, Any]:
    record = get_import(import_id)
    if not record:
        return {"ok": False, "error": "import_not_found"}
    if record.get("committed"):
        return {"ok": False, "error": "already_committed", "import_id": import_id}
    accepted = (record.get("report") or {}).get("accepted") or []
    if not accepted:
        return {"ok": False, "error": "nothing_to_commit", "import_id": import_id}

    tab_id = str(record.get("tab_id"))
    from institutional_warehouse import gateway

    result = gateway.write(
        tab_id,
        accepted,
        source=str(record.get("source") or "manual_import"),
        actor=actor,
        import_id=import_id,
        reason=f"import:{import_id}",
    )
    db.execute("UPDATE wh_imports SET committed = 1 WHERE id = ?", (import_id,))
    audit.record("import", tab_id=tab_id, actor=actor,
                 detail={"stage": "committed", "import_id": import_id, **{
                     k: result.get(k) for k in ("inserted", "updated", "unchanged", "skipped")}})

    recalc = None
    if recalculate:
        from institutional_warehouse.formulas import recalculate as run_formulas

        recalc = run_formulas(actor=actor, stages=stages_for(tab_id))
    return {"ok": True, "import_id": import_id, "tab": tab_id, **result, "recalculated": recalc}


def stages_for(tab_id: str) -> list[str]:
    if tab_id in ("financials_annual", "financials_quarterly"):
        return ["statement_derivations", "ratios", "annual_sector_ratios", "valuation", "factors", "quality"]
    if tab_id == "daily_market_history":
        return ["market_derivations", "valuation", "factors", "quality"]
    if tab_id == "consensus":
        return ["consensus_derivations", "valuation", "factors", "quality"]
    if tab_id == "company_master":
        return ["annual_sector_ratios", "valuation", "quality"]
    return ["quality"]


def import_and_commit(
    tab_id: str,
    rows: Sequence[dict[str, Any]],
    *,
    actor: str = "admin",
    source: str = "manual_import",
    recalculate: bool = False,
) -> dict[str, Any]:
    staged = stage(tab_id, rows=list(rows), actor=actor, source=source)
    if not staged.get("ok"):
        return staged
    if staged.get("accepted", 0) == 0:
        return {**staged, "committed": False}
    committed = commit(staged["import_id"], actor=actor, recalculate=recalculate)
    return {**staged, **committed, "committed": True}


def recent_imports(*, tab_id: Optional[str] = None, limit: int = 25) -> dict[str, Any]:
    clause = " WHERE tab_id = ?" if tab_id else ""
    params: tuple[Any, ...] = (tab_id,) if tab_id else ()
    rows = db.query(
        f"SELECT id, created_at, tab_id, actor, source, rows_seen, rows_accepted, rows_rejected,"
        f" committed FROM wh_imports{clause} ORDER BY created_at DESC LIMIT ?",
        (*params, max(1, min(int(limit), 200))),
    )
    return {"ok": True, "imports": [{**r, "committed": bool(r.get("committed"))} for r in rows]}


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------


def export_csv(
    tab_id: str,
    *,
    entity: Optional[str] = None,
    filters: Optional[dict[str, Any]] = None,
    search: Optional[str] = None,
    limit: int = 5000,
    actor: str = "admin",
) -> dict[str, Any]:
    tab = get_tab(tab_id)
    page = store.fetch(tab.id, entity=entity, filters=filters, search=search, limit=limit)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    columns = [c.key for c in tab.columns]
    writer.writerow([tab.column(c).label for c in columns])
    for row in page["rows"]:
        writer.writerow(["" if row.get(c) is None else row.get(c) for c in columns])
    audit.record("export", tab_id=tab.id, actor=actor, detail={"rows": len(page["rows"])})
    return {
        "ok": True,
        "tab": tab.id,
        "filename": f"{tab.id}.csv",
        "rows": len(page["rows"]),
        "total": page["total"],
        "csv": buffer.getvalue(),
    }
