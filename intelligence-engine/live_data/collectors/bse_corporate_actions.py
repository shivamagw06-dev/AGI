"""BSE Corporate Actions collector — resilient HTML / CSV / JSON parsers."""

from __future__ import annotations

import csv
import html as html_lib
import io
import json
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from live_data import store
from live_data.collectors.base import collector_envelope, fallback_to_snapshot, http_get, run_with_retry
from live_data.qa import qa_corporate_actions
from live_data.schema import DEFAULT_RETRY

COLLECTOR_ID = "lidi_bse_corporate_actions_v1"
SOURCE_ID = "bse_corporate_actions"
OFFICIAL = "BSE India"
SAMPLES = Path(__file__).resolve().parents[1] / "samples"

# Public BSE surfaces — HTML landing, CSV-ish exports, and JSON APIs.
# When BSE API returns SPA/WAF shells, NSE corporate-actions JSON is used as
# a transparent exchange fallback (same economic events; source tagged).
def _bse_urls() -> list[str]:
    today = datetime.utcnow().date()
    start = (today - timedelta(days=120)).strftime("%Y%m%d")
    fdate = (today - timedelta(days=120)).strftime("%d/%m/%Y")
    tdate = today.strftime("%d/%m/%Y")
    nse_from = (today - timedelta(days=60)).strftime("%d-%m-%Y")
    nse_to = today.strftime("%d-%m-%Y")
    qs = urlencode(
        {
            "Fdate": fdate,
            "TDate": tdate,
            "Purposecode": "",
            "ddlcategorys": "",
            "ddlindicators": "",
            "scripcode": "",
            "segment": "0",
            "strSearch": "S",
        }
    )
    return [
        f"https://api.bseindia.com/BseIndiaAPI/api/DefaultData/GetData?{qs}",
        f"https://api.bseindia.com/BseIndiaAPI/api/Corpact/w?{qs}",
        "https://www.bseindia.com/corporates/corporate_act.aspx",
        "https://www.bseindia.com/corporates/corporates_act.html",
        # NSE exchange fallback — official JSON (BSE API often returns WAF HTML).
        (
            "https://www.nseindia.com/api/corporates-corporateActions?"
            + urlencode({"index": "equities", "from_date": nse_from, "to_date": nse_to})
        ),
        "https://www.nseindia.com/api/corporates-corporateActions?index=equities",
        f"https://www.bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_{start}.ZIP",  # may 404; ignored
    ]


# Browser-like headers — BSE API returns HTTP 403 for bot-style UAs.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.bseindia.com/corporates/corporate_act.aspx",
    "Origin": "https://www.bseindia.com",
    "Connection": "keep-alive",
}


def _bse_session_opener():
    """Cookie jar via BSE homepage — required for api.bseindia.com (avoids 403)."""
    import http.cookiejar
    import urllib.request

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    try:
        http_get(
            "https://www.bseindia.com/",
            headers={
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "text/html,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            },
            timeout=15,
            opener=opener,
        )
    except Exception:
        pass
    return opener

NAME_MAP = {
    "INFOSYS LTD": "INFY",
    "INFOSYS LIMITED": "INFY",
    "TCS LTD": "TCS",
    "TATA CONSULTANCY SERVICES LTD": "TCS",
    "TATA CONSULTANCY SERVICES LIMITED": "TCS",
    "RELIANCE INDUSTRIES LTD": "RELIANCE",
    "RELIANCE INDUSTRIES LIMITED": "RELIANCE",
    "HDFC BANK LTD": "HDFCBANK",
    "HDFC BANK LIMITED": "HDFCBANK",
    "ICICI BANK LTD": "ICICIBANK",
    "ICICI BANK LIMITED": "ICICIBANK",
    "WIPRO LTD": "WIPRO",
    "WIPRO LIMITED": "WIPRO",
}


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t == "table":
            self._table = []
        elif t == "tr" and self._table is not None:
            self._row = []
        elif t in {"td", "th"} and self._row is not None:
            self._cell = []
            self._in_cell = True

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in {"td", "th"} and self._in_cell and self._row is not None:
            text = html_lib.unescape(" ".join(self._cell or []).strip())
            text = re.sub(r"\s+", " ", text)
            self._row.append(text)
            self._cell = None
            self._in_cell = False
        elif t == "tr" and self._row is not None and self._table is not None:
            if any(c.strip() for c in self._row):
                self._table.append(self._row)
            self._row = None
        elif t == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if self._in_cell and self._cell is not None:
            self._cell.append(data)


def collect_bse_corporate_actions(
    *,
    injected_csv: str | bytes | None = None,
    allow_recorded_sample: bool = False,
) -> dict[str, Any]:
    mode = "live"
    text = None
    raw = None
    url_used = None
    parse_path = "csv"
    try:
        if injected_csv is not None:
            mode = "injected"
            raw = injected_csv.encode("utf-8") if isinstance(injected_csv, str) else injected_csv
            text = raw.decode("utf-8", errors="replace")
        else:

            def _fetch() -> tuple[bytes, str]:
                nonlocal url_used
                last = None
                opener = _bse_session_opener()
                # NSE endpoints need an NSE cookie jar (separate from BSE).
                nse_opener = None
                for url in _bse_urls():
                    if url.endswith(".ZIP"):
                        continue  # reserved for future bhav-style exports
                    try:
                        use_opener = opener
                        headers = HEADERS
                        if "nseindia.com" in url:
                            if nse_opener is None:
                                from live_data.collectors.base import nse_session_opener

                                nse_opener = nse_session_opener()
                            use_opener = nse_opener
                            headers = {
                                "User-Agent": HEADERS["User-Agent"],
                                "Accept": "application/json,text/plain,*/*",
                                "Accept-Language": "en-US,en;q=0.9",
                                "Referer": (
                                    "https://www.nseindia.com/companies-listing/"
                                    "corporate-filings-actions"
                                ),
                            }
                        data = http_get(url, headers=headers, timeout=30, opener=use_opener)
                        lower = data[:8000].lower()
                        # Accept JSON arrays/objects immediately (BSE or NSE).
                        stripped = data.lstrip()[:1]
                        if stripped in (b"{", b"["):
                            url_used = url
                            return data, url
                        # Reject tiny WAF/error HTML shells from api.bseindia.com
                        if b"<!doctype html" in lower or b"<html" in lower:
                            if b"<table" not in lower and b"ex date" not in lower and b"purpose" not in lower:
                                last = RuntimeError("bse_actions_html_without_tabular_export")
                                continue
                        url_used = url
                        return data, url
                    except Exception as exc:  # noqa: BLE001
                        last = exc
                raise RuntimeError(f"bse_actions_fetch_failed:{last}")

            try:
                policy = {"max_attempts": 1, "backoff_seconds": [0]} if allow_recorded_sample else DEFAULT_RETRY
                raw, url_used = run_with_retry(_fetch, retry_policy=policy)
                text = raw.decode("utf-8", errors="replace")
                if url_used and "nseindia.com" in str(url_used):
                    mode = "live_nse_fallback"
            except Exception as live_exc:
                if allow_recorded_sample:
                    sample = SAMPLES / "bse_corporate_actions.csv"
                    mode = "recorded_sample"
                    raw = sample.read_bytes()
                    text = raw.decode("utf-8")
                    url_used = str(sample)
                    parse_path = "csv"
                else:
                    fb = fallback_to_snapshot(
                        collector_id=COLLECTOR_ID,
                        source_id=SOURCE_ID,
                        entity="LATEST",
                        reason=str(live_exc)[:200],
                    )
                    store.update_collector_health(
                        COLLECTOR_ID,
                        source=SOURCE_ID,
                        last_failure=store.utc_now(),
                        failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
                        last_error=str(live_exc)[:200],
                        version=COLLECTOR_ID,
                        frequency="daily",
                        retry_policy=DEFAULT_RETRY,
                    )
                    return fb or {
                        "ok": False,
                        "collector_id": COLLECTOR_ID,
                        "source_id": SOURCE_ID,
                        "official_source": OFFICIAL,
                        "reason": "live_unavailable_no_snapshot",
                        "error": str(live_exc)[:240],
                        "fixture": False,
                        "fabricated": False,
                        "transparent_insufficiency": True,
                    }

        assert text is not None and raw is not None
        actions, effective, parse_path = _parse_actions_any(text)
        if not actions and mode == "live":
            raise RuntimeError("bse_actions_html_without_tabular_export")

        # Append-merge into durable history (never drop prior actions).
        hist = _merge_history(actions)
        qa = qa_corporate_actions(hist)

        file_rec = store.put_raw_file(
            SOURCE_ID,
            "corporate_actions.csv" if parse_path == "csv" else "corporate_actions.json",
            raw if parse_path != "json" else json.dumps({"actions": hist}, default=str).encode("utf-8"),
            meta={"mode": mode, "url": url_used, "parse_path": parse_path, "qa": qa},
        )
        env = collector_envelope(
            collector_id=COLLECTOR_ID,
            source_id=SOURCE_ID,
            official_source=OFFICIAL,
            payload={
                "effective_date": effective,
                "actions": hist,
                "action_count": len(hist),
                "url": url_used,
                "parse_path": parse_path,
                "qa": qa,
            },
            effective_date=effective,
            checksum=file_rec["checksum"],
            mode=mode,
            downloaded_files=[file_rec],
            confidence=0.9 if mode == "live" else 0.75,
        )
        store.put_raw(SOURCE_ID, "LATEST", env)
        store.put_object(
            SOURCE_ID,
            "HISTORY",
            {"ok": True, "actions": hist, "qa": qa, "updated_at": store.utc_now()},
        )
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            version=COLLECTOR_ID,
            frequency="daily",
            retry_policy=DEFAULT_RETRY,
            last_success=store.utc_now(),
            last_checksum=file_rec["checksum"],
            success_count=(store.get_collector_health(COLLECTOR_ID).get("success_count") or 0) + 1,
            downloaded_files=[file_rec.get("path")],
            metadata={"action_count": len(hist), "mode": mode, "parse_path": parse_path, "qa": qa},
        )
        return env
    except Exception as exc:  # noqa: BLE001
        fb = fallback_to_snapshot(
            collector_id=COLLECTOR_ID, source_id=SOURCE_ID, entity="LATEST", reason=str(exc)[:200]
        )
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            last_failure=store.utc_now(),
            failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
            last_error=str(exc)[:200],
        )
        return fb or {
            "ok": False,
            "collector_id": COLLECTOR_ID,
            "source_id": SOURCE_ID,
            "official_source": OFFICIAL,
            "reason": "collect_failed",
            "error": str(exc)[:240],
            "fixture": False,
            "fabricated": False,
            "transparent_insufficiency": True,
        }


def _parse_actions_any(text: str) -> tuple[list[dict[str, Any]], str | None, str]:
    stripped = text.lstrip()
    # JSON API
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            actions, effective = _parse_actions_json(json.loads(stripped))
            if actions:
                return actions, effective, "json"
        except Exception:
            pass
    # CSV / TSV
    if "Security Code" in text or "Security Name" in text or "Ex Date" in text:
        try:
            actions, effective = _parse_actions_csv(text)
            if actions:
                return actions, effective, "csv"
        except Exception:
            pass
    # HTML tables
    actions, effective = _parse_actions_html(text)
    if actions:
        return actions, effective, "html_table"
    # Last resort: regex rows mentioning Dividend/Bonus/Split
    actions, effective = _parse_actions_regex(text)
    return actions, effective, "regex" if actions else "none"


def _parse_actions_json(obj: Any) -> tuple[list[dict[str, Any]], str | None]:
    rows: list[Any] = []
    if isinstance(obj, list):
        rows = obj
    elif isinstance(obj, dict):
        for key in ("Table", "Table1", "data", "Data", "result", "Result", "CorporateAction"):
            if isinstance(obj.get(key), list):
                rows = obj[key]
                break
        if not rows:
            # Sometimes nested under "d"
            d = obj.get("d")
            if isinstance(d, str):
                try:
                    return _parse_actions_json(json.loads(d))
                except Exception:
                    pass
            elif isinstance(d, list):
                rows = d
            elif isinstance(d, dict):
                return _parse_actions_json(d)
    actions: list[dict[str, Any]] = []
    effective = None
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        # Normalise keys case-insensitively
        lower = {str(k).strip().lower().replace(" ", ""): v for k, v in raw.items()}
        name = str(
            lower.get("securityname")
            or lower.get("scrip_name")
            or lower.get("longname")
            or lower.get("comp")  # NSE corporates-corporateActions
            or lower.get("company")
            or lower.get("name")
            or ""
        ).strip()
        purpose = str(
            lower.get("purpose")
            or lower.get("particular")
            or lower.get("details")
            or lower.get("subject")  # NSE
            or lower.get("desc")
            or ""
        ).strip()
        ex = str(
            lower.get("exdate")
            or lower.get("ex_date")
            or lower.get("exdt")
            or ""
        ).strip()
        code = (
            lower.get("securitycode")
            or lower.get("scrip_code")
            or lower.get("scripcode")
            or lower.get("symbol")
            or lower.get("isin")
        )
        record = str(
            lower.get("recorddate")
            or lower.get("record_date")
            or lower.get("recdate")  # NSE
            or ""
        ).strip()
        if not purpose and not ex:
            continue
        ed = _parse_date(ex)
        if ed and not effective:
            effective = ed
        actions.append(_action_row(name=name, purpose=purpose, ex=ed, code=code, record=_parse_date(record)))
    return actions, effective


def _parse_actions_html(text: str) -> tuple[list[dict[str, Any]], str | None]:
    parser = _TableParser()
    try:
        parser.feed(text)
    except Exception:
        return [], None
    actions: list[dict[str, Any]] = []
    effective = None
    for table in parser.tables:
        if len(table) < 2:
            continue
        header = [c.lower() for c in table[0]]
        # Identify columns
        def _col(*names: str) -> int | None:
            for i, h in enumerate(header):
                for n in names:
                    if n in h:
                        return i
            return None

        i_name = _col("security name", "scrip name", "company", "name")
        i_code = _col("security code", "scrip code", "code")
        i_purpose = _col("purpose", "particular", "details")
        i_ex = _col("ex date", "ex-date", "exdate")
        i_rec = _col("record date", "recorddate")
        # Heuristic: any header mentioning purpose / dividend
        if i_purpose is None and not any("purpose" in h or "dividend" in h for h in header):
            # Try scanning body for purpose-like cells
            if not any(
                any(k in " ".join(r).lower() for k in ("dividend", "bonus", "split", "rights")) for r in table[1:6]
            ):
                continue
        for row in table[1:]:
            def _at(idx: int | None) -> str:
                if idx is None or idx >= len(row):
                    return ""
                return row[idx]

            name = _at(i_name) if i_name is not None else (row[1] if len(row) > 1 else "")
            purpose = _at(i_purpose) if i_purpose is not None else " ".join(row)
            if not any(k in purpose.lower() for k in ("dividend", "bonus", "split", "right", "buyback", "agm")):
                if i_purpose is None:
                    continue
            ex = _parse_date(_at(i_ex)) if i_ex is not None else _first_date_in(row)
            if ex and not effective:
                effective = ex
            code = _at(i_code) if i_code is not None else (row[0] if row else "")
            actions.append(
                _action_row(
                    name=name,
                    purpose=purpose if i_purpose is not None else _guess_purpose(purpose),
                    ex=ex,
                    code=code,
                    record=_parse_date(_at(i_rec)) if i_rec is not None else None,
                )
            )
    return actions, effective


def _parse_actions_regex(text: str) -> tuple[list[dict[str, Any]], str | None]:
    actions: list[dict[str, Any]] = []
    effective = None
    # Rough pattern: CODE NAME DATE Purpose...
    pat = re.compile(
        r"(\d{5,6})\s+([A-Z][A-Z0-9 &.\-]{3,60}?)\s+(\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}|\d{4}-\d{2}-\d{2})\s+((?:Dividend|Bonus|Split|Rights|Buy\s*Back)[^<\n]{0,80})",
        re.I,
    )
    for m in pat.finditer(text):
        ed = _parse_date(m.group(3))
        if ed and not effective:
            effective = ed
        actions.append(
            _action_row(name=m.group(2).strip(), purpose=m.group(4).strip(), ex=ed, code=m.group(1), record=None)
        )
    return actions, effective


def _parse_actions_csv(text: str) -> tuple[list[dict[str, Any]], str | None]:
    reader = csv.DictReader(io.StringIO(text))
    actions = []
    effective = None
    for raw in reader:
        row = {}
        for k, v in raw.items():
            if k is None:
                continue
            if isinstance(v, list):
                v = v[0] if v else ""
            row[str(k).strip()] = str(v or "").strip()
        name = row.get("Security Name") or row.get("SecurityName") or ""
        purpose = row.get("Purpose") or row.get("purpose") or ""
        ex = row.get("Ex Date") or row.get("ExDate") or ""
        code = row.get("Security Code") or row.get("SecurityCode")
        if not purpose:
            continue
        ed = _parse_date(ex)
        if ed and not effective:
            effective = ed
        actions.append(
            _action_row(
                name=name,
                purpose=purpose,
                ex=ed,
                code=code,
                record=_parse_date(row.get("Record Date") or ""),
            )
        )
    return actions, effective


def _action_row(
    *,
    name: str,
    purpose: str,
    ex: str | None,
    code: Any,
    record: str | None,
) -> dict[str, Any]:
    sym = NAME_MAP.get(name.upper()) or NAME_MAP.get(name) or None
    return {
        "symbol": sym,
        "security_code": str(code) if code is not None else None,
        "security_name": name,
        "purpose": purpose,
        "ex_date": ex,
        "record_date": record,
        "effective_date": ex,
        "action_type": _classify(purpose),
        "source": SOURCE_ID,
    }


def _merge_history(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prev = store.get_object(SOURCE_ID, "HISTORY") or {}
    existing = list(prev.get("actions") or [])
    by_key: dict[str, dict[str, Any]] = {}
    for a in existing + actions:
        key = "|".join(
            [
                str(a.get("security_code") or ""),
                str(a.get("security_name") or ""),
                str(a.get("ex_date") or ""),
                str(a.get("purpose") or "")[:80],
            ]
        )
        by_key.setdefault(key, a)
    return sorted(by_key.values(), key=lambda x: str(x.get("ex_date") or ""), reverse=True)


def _first_date_in(cells: list[str]) -> str | None:
    for c in cells:
        d = _parse_date(c)
        if d:
            return d
    return None


def _guess_purpose(blob: str) -> str:
    b = blob.lower()
    for token in ("dividend", "bonus", "split", "rights", "buyback"):
        if token in b:
            # return surrounding snippet
            i = b.find(token)
            return blob[max(0, i - 10) : i + 40].strip()
    return blob[:80]


def _parse_date(s: str) -> str | None:
    s = str(s or "").strip()
    if not s:
        return None
    # JSON /Date(1719878400000)/
    m = re.search(r"/Date\((\-?\d+)\)/", s)
    if m:
        try:
            return datetime.utcfromtimestamp(int(m.group(1)) / 1000.0).date().isoformat()
        except Exception:
            pass
    for fmt in ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    return None


def _classify(purpose: str) -> str:
    p = purpose.lower()
    if "split" in p or "face value" in p:
        return "split"
    if "bonus" in p:
        return "bonus"
    if "right" in p:
        return "rights"
    if "dividend" in p or "div " in p:
        return "dividend"
    if "buyback" in p or "buy back" in p:
        return "buyback"
    return "corporate_action"
