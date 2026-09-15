"""Company Investor Relations collector — discover & catalogue IR documents."""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from live_data import store
from live_data.collectors.base import collector_envelope, fallback_to_snapshot, http_get, run_with_retry
from live_data.qa import qa_documents
from live_data.schema import DEFAULT_RETRY

COLLECTOR_ID = "lidi_company_ir_v1"
SOURCE_ID = "company_ir"
OFFICIAL = "Company IR websites"
SAMPLES = Path(__file__).resolve().parents[1] / "samples"

IR_ENTRYPOINTS: dict[str, str] = {
    "INFY": "https://www.infosys.com/investors.html",
    "TCS": "https://www.tcs.com/investor-relations",
    "RELIANCE": "https://www.ril.com/InvestorRelations.aspx",
    "HDFCBANK": "https://www.hdfcbank.com/personal/about-us/investor-relations",
    "WIPRO": "https://www.wipro.com/investors/",
    "ICICIBANK": "https://www.icicibank.com/about-us/investor-relations",
    "SBIN": "https://sbi.co.in/web/investor-relations",
    "ITC": "https://www.itcportal.com/investor/index.aspx",
}

# Secondary deep links often richer than the IR hub.
IR_SECONDARY: dict[str, list[str]] = {
    "INFY": [
        "https://www.infosys.com/investors/reports-filings.html",
        "https://www.infosys.com/investors/reports-filings/annual-report.html",
        "https://www.infosys.com/investors/reports-filings/quarterly-results.html",
    ],
    "TCS": [
        "https://www.tcs.com/investor-relations/financial-statements",
    ],
    "WIPRO": [
        "https://www.wipro.com/investors/annual-reports/",
        "https://www.wipro.com/investors/quarterly-results/",
    ],
}

DOC_EXT = (".pdf", ".xlsx", ".xls", ".doc", ".docx", ".ppt", ".pptx", ".zip")


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (href, anchor_text)
        self._in_a = False
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = ""
        for k, v in attrs:
            if k.lower() == "href" and v:
                href = v.strip()
                break
        if href:
            self._in_a = True
            self._href = href
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._in_a:
            self.links.append((self._href, " ".join(self._text).strip()))
            self._in_a = False
            self._href = ""
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._text.append(data)


def collect_company_ir(
    *,
    ticker: str = "INFY",
    injected_json: dict[str, Any] | str | None = None,
    allow_recorded_sample: bool = False,
    download_files: bool = True,
    max_downloads: int = 8,
) -> dict[str, Any]:
    t = str(ticker or "INFY").upper()
    mode = "live"
    payload_obj = None
    raw = None
    url_used = IR_ENTRYPOINTS.get(t)
    try:
        if injected_json is not None:
            mode = "injected"
            if isinstance(injected_json, str):
                payload_obj = json.loads(injected_json)
                raw = injected_json.encode("utf-8")
            else:
                payload_obj = injected_json
                raw = json.dumps(injected_json).encode("utf-8")
        else:

            def _fetch_hub() -> bytes:
                if not url_used:
                    raise RuntimeError(f"no_ir_entrypoint:{t}")
                return http_get(
                    url_used,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)", "Accept": "text/html,*/*"},
                    timeout=30,
                )

            try:
                policy = {"max_attempts": 1, "backoff_seconds": [0]} if allow_recorded_sample else DEFAULT_RETRY
                html = run_with_retry(_fetch_hub, retry_policy=policy)
                pages: list[tuple[str, bytes]] = [(url_used or "", html)]
                # Follow secondary IR pages (bounded)
                for sec in (IR_SECONDARY.get(t) or [])[:3]:
                    try:
                        pages.append(
                            (
                                sec,
                                http_get(
                                    sec,
                                    headers={
                                        "User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)",
                                        "Accept": "text/html,*/*",
                                    },
                                    timeout=25,
                                ),
                            )
                        )
                    except Exception:
                        continue
                docs = _discover_documents(pages, ticker=t)
                # Dedupe against prior catalogue
                docs = _dedupe_docs(t, docs)
                downloaded: list[dict[str, Any]] = []
                if download_files and docs:
                    downloaded = _download_new_docs(t, docs, limit=max_downloads)
                payload_obj = {
                    "effective_date": store.utc_now()[:10],
                    "ticker": t,
                    "documents": docs,
                    "downloaded": downloaded,
                    "document_count": len(docs),
                    "downloaded_count": len(downloaded),
                    "ir_page_reachable": True,
                    "structured_filings": "discovered" if docs else "UNKNOWN",
                    "note": "IR HTML parsed for document links; historical versions retained by URL/checksum",
                    "pages_scanned": len(pages),
                }
                raw = json.dumps(payload_obj).encode("utf-8")
                mode = "live" if docs else "live_probe"
            except Exception as live_exc:
                if allow_recorded_sample and t == "INFY":
                    sample = SAMPLES / "company_ir_infosys.json"
                    mode = "recorded_sample"
                    raw = sample.read_bytes()
                    payload_obj = json.loads(raw.decode("utf-8"))
                    url_used = str(sample)
                else:
                    fb = fallback_to_snapshot(
                        collector_id=COLLECTOR_ID,
                        source_id=SOURCE_ID,
                        entity=t,
                        reason=str(live_exc)[:200],
                    )
                    store.update_collector_health(
                        COLLECTOR_ID,
                        source=SOURCE_ID,
                        last_failure=store.utc_now(),
                        failure_count=(store.get_collector_health(COLLECTOR_ID).get("failure_count") or 0) + 1,
                        last_error=str(live_exc)[:200],
                        version=COLLECTOR_ID,
                        frequency="event_driven",
                        retry_policy=DEFAULT_RETRY,
                    )
                    return fb or {
                        "ok": False,
                        "collector_id": COLLECTOR_ID,
                        "source_id": SOURCE_ID,
                        "official_source": OFFICIAL,
                        "entity": t,
                        "reason": "live_unavailable_no_snapshot",
                        "error": str(live_exc)[:240],
                        "fixture": False,
                        "fabricated": False,
                        "transparent_insufficiency": True,
                    }

        assert payload_obj is not None and raw is not None
        docs = list(payload_obj.get("documents") or [])
        effective = payload_obj.get("effective_date")
        qa = qa_documents(docs)
        # Persist catalogue object for incremental history
        store.put_object(
            SOURCE_ID,
            t,
            {
                "ticker": t,
                "documents": docs,
                "updated_at": store.utc_now(),
                "qa": qa,
            },
        )
        file_rec = store.put_raw_file(SOURCE_ID, f"{t}_ir.json", raw, meta={"mode": mode, "url": url_used})
        env = collector_envelope(
            collector_id=COLLECTOR_ID,
            source_id=SOURCE_ID,
            official_source=OFFICIAL,
            payload={
                "effective_date": effective,
                "ticker": t,
                "documents": docs,
                "document_count": len(docs),
                "downloaded_count": int(payload_obj.get("downloaded_count") or 0),
                "downloaded": payload_obj.get("downloaded") or [],
                "url": url_used,
                "structured_filings": payload_obj.get("structured_filings"),
                "note": payload_obj.get("note"),
                "qa": qa,
            },
            effective_date=effective,
            checksum=file_rec["checksum"],
            mode=mode,
            downloaded_files=[file_rec],
            confidence=0.85 if mode.startswith("live") else 0.75,
        )
        store.put_raw(SOURCE_ID, t, env)
        store.update_collector_health(
            COLLECTOR_ID,
            source=SOURCE_ID,
            version=COLLECTOR_ID,
            frequency="event_driven",
            retry_policy=DEFAULT_RETRY,
            last_success=store.utc_now(),
            last_checksum=file_rec["checksum"],
            success_count=(store.get_collector_health(COLLECTOR_ID).get("success_count") or 0) + 1,
            downloaded_files=[file_rec.get("path")],
            metadata={
                "ticker": t,
                "document_count": len(docs),
                "downloaded_count": int(payload_obj.get("downloaded_count") or 0),
                "mode": mode,
                "qa": qa,
            },
        )
        return env
    except Exception as exc:  # noqa: BLE001
        fb = fallback_to_snapshot(
            collector_id=COLLECTOR_ID, source_id=SOURCE_ID, entity=t, reason=str(exc)[:200]
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
            "entity": t,
            "reason": "collect_failed",
            "error": str(exc)[:240],
            "fixture": False,
            "fabricated": False,
            "transparent_insufficiency": True,
        }


def _discover_documents(pages: list[tuple[str, bytes]], *, ticker: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for base, html in pages:
        text = html.decode("utf-8", errors="replace")
        parser = _LinkParser()
        try:
            parser.feed(text)
            link_pairs = list(parser.links)
        except Exception:
            link_pairs = []
        # Regex fallback for bare PDF URLs
        for m in re.finditer(r"""(?:href|src)=["']([^"']+\.(?:pdf|xlsx?|docx?|pptx?))["']""", text, re.I):
            link_pairs.append((m.group(1), ""))
        for href, anchor in link_pairs:
            abs_url = urljoin(base, href)
            if not _looks_like_doc(abs_url, anchor):
                continue
            norm = abs_url.split("#")[0]
            if norm in seen:
                continue
            seen.add(norm)
            title = anchor or Path(urlparse(norm).path).name
            docs.append(
                {
                    "doc_type": _classify_doc(norm, title),
                    "title": title[:240],
                    "url": norm,
                    "published_at": _guess_date(norm, title),
                    "ticker": ticker,
                    "source": SOURCE_ID,
                }
            )
    # Prefer classified IR docs; cap catalogue size
    priority = {
        "annual_report": 0,
        "quarterly_results": 1,
        "investor_presentation": 2,
        "earnings_transcript": 3,
        "esg_report": 4,
        "credit_rating": 5,
        "press_release": 6,
        "other": 9,
    }
    docs.sort(key=lambda d: (priority.get(str(d.get("doc_type")), 9), str(d.get("published_at") or ""), d["url"]))
    return docs[:200]


def _looks_like_doc(url: str, anchor: str) -> bool:
    u = url.lower()
    a = (anchor or "").lower()
    if any(u.endswith(ext) or ext + "?" in u for ext in DOC_EXT):
        return True
    # Some IR sites use download handlers without extension
    if any(k in u or k in a for k in ("annual-report", "investor-presentation", "quarterly-result", "transcript")):
        if "javascript:" in u or u.startswith("#"):
            return False
        return True
    return False


def _classify_doc(url: str, title: str) -> str:
    blob = f"{url} {title}".lower()
    if any(k in blob for k in ("transcript", "earnings-call", "conference-call")):
        return "earnings_transcript"
    if any(k in blob for k in ("investor-presentation", "presentation", "ppt", "deck")):
        return "investor_presentation"
    if any(k in blob for k in ("annual-report", "annual_report", "integrated-report")):
        return "annual_report"
    if any(k in blob for k in ("quarterly", "q1-", "q2-", "q3-", "q4-", "financial-result", "results")):
        return "quarterly_results"
    if any(k in blob for k in ("esg", "sustainability", "brsr")):
        return "esg_report"
    if any(k in blob for k in ("rating", "credit-rating", "moodys", "crisil", "icra")):
        return "credit_rating"
    if any(k in blob for k in ("press-release", "press_release", "news")):
        return "press_release"
    return "other"


def _guess_date(url: str, title: str) -> str | None:
    blob = f"{url} {title}"
    m = re.search(r"(20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})", blob)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(20\d{2})", blob)
    if m:
        return f"{m.group(1)}-01-01"
    return None


def _dedupe_docs(ticker: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prev = store.get_object(SOURCE_ID, ticker) or {}
    existing = {str(d.get("url")): d for d in (prev.get("documents") or []) if d.get("url")}
    for d in docs:
        existing.setdefault(str(d["url"]), d)
    return list(existing.values())


def _download_new_docs(ticker: str, docs: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    """Download unseen docs; skip if checksum already stored."""
    catalogue = store.get_object(SOURCE_ID, f"{ticker}_DOWNLOADS") or {"by_url": {}}
    by_url: dict[str, Any] = dict(catalogue.get("by_url") or {})
    out: list[dict[str, Any]] = []
    for d in docs:
        if len(out) >= limit:
            break
        url = str(d.get("url") or "")
        if not url or not url.lower().endswith(".pdf"):
            continue
        if url in by_url:
            continue
        try:
            data = http_get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)", "Accept": "application/pdf,*/*"},
                timeout=45,
            )
            if len(data) < 500 or data[:4] == b"<htm" or data[:1] == b"<":
                continue  # likely HTML error page
            digest = hashlib.sha256(data).hexdigest()
            # Skip identical checksum already seen under another URL
            if any(v.get("checksum") == digest for v in by_url.values()):
                by_url[url] = {"checksum": digest, "skipped": "duplicate_checksum", "bytes": len(data)}
                continue
            name = f"{ticker}_{d.get('doc_type')}_{digest[:12]}.pdf"
            rec = store.put_raw_file(SOURCE_ID, name, data, meta={"url": url, "doc_type": d.get("doc_type")})
            row = {
                "url": url,
                "checksum": digest,
                "bytes": len(data),
                "doc_type": d.get("doc_type"),
                "path": rec.get("path"),
                "downloaded_at": store.utc_now(),
            }
            by_url[url] = row
            out.append(row)
            d["checksum"] = digest
            d["local_path"] = rec.get("path")
        except Exception as exc:  # noqa: BLE001
            by_url[url] = {"error": str(exc)[:160], "failed_at": store.utc_now()}
    store.put_object(SOURCE_ID, f"{ticker}_DOWNLOADS", {"by_url": by_url, "updated_at": store.utc_now()})
    return out
