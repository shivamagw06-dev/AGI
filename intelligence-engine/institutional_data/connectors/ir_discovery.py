"""IR Discovery Engine — auto-discover IR portals and institutional documents."""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

from institutional_data.connectors.base import Connector, ConnectorResult

DOC_CLASSES = (
    "annual_report",
    "quarterly_report",
    "investor_presentation",
    "earnings_transcript",
    "esg_report",
    "governance_report",
    "press_release",
    "fact_sheet",
    "corporate_presentation",
)

DOC_EXT = (".pdf", ".xlsx", ".xls", ".ppt", ".pptx", ".doc", ".docx", ".zip")

# Seed hubs + discovery templates (not a closed allow-list — discovery expands).
SEED_HUBS: dict[str, str] = {
    "INFY": "https://www.infosys.com/investors.html",
    "TCS": "https://www.tcs.com/investor-relations",
    "RELIANCE": "https://www.ril.com/InvestorRelations.aspx",
    "HDFCBANK": "https://www.hdfcbank.com/personal/about-us/investor-relations",
    "WIPRO": "https://www.wipro.com/investors/",
    "ICICIBANK": "https://www.icicibank.com/about-us/investor-relations",
    "SBIN": "https://sbi.co.in/web/investor-relations",
    "ITC": "https://www.itcportal.com/investor/index.aspx",
}

DISCOVERY_TEMPLATES = (
    "https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
    "https://www.bseindia.com/stock-share-price/{symbol_l}/",
)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
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

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._text.append(data)


class IRDiscoveryConnector(Connector):
    connector_id = "lidi_company_ir_v1"
    source_id = "company_ir"
    official_source = "Company IR / Exchange corporate pages"

    def collect(self, **kwargs: Any) -> ConnectorResult:
        entity = str(kwargs.get("entity") or kwargs.get("ticker") or "INFY").upper()
        t0 = time.time()
        max_downloads = int(kwargs.get("max_downloads") or 6)
        download = bool(kwargs.get("download_files", True))

        hubs = self.discover_hubs(entity)
        pages: list[tuple[str, bytes]] = []
        errors: list[str] = []
        for hub in hubs[:5]:
            try:
                from live_data.collectors.base import http_get

                html = http_get(
                    hub,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)", "Accept": "text/html,*/*"},
                    timeout=30,
                )
                pages.append((hub, html))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"hub:{hub}:{str(exc)[:80]}")

        docs = self.identify_documents(pages, ticker=entity)
        docs = self.deduplicate(entity, docs)
        downloaded = []
        if download and docs:
            downloaded = self.download_and_archive(entity, docs, limit=max_downloads)

        ok = bool(docs) or bool(downloaded)
        return ConnectorResult(
            ok=ok,
            connector_id=self.connector_id,
            source_id=self.source_id,
            records=docs,
            mode="live",
            error=None if ok else (errors[0] if errors else "ir_no_documents"),
            diagnostics={
                "entity": entity,
                "hubs": hubs,
                "document_count": len(docs),
                "downloaded": len(downloaded),
                "errors": errors,
                "latency_ms": int((time.time() - t0) * 1000),
                "parse_path": "ir_discovery",
            },
            coverage_pct=min(100.0, 12.5 * len({d.get("doc_type") for d in docs})),
            repair_items=[]
            if ok
            else [{"company": entity, "reason": "ir_documents_missing", "connector": self.connector_id, "priority": 3}],
        )

    def validate(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        if not records:
            return {"ok": False, "reason": "empty"}
        bad = [r for r in records if not r.get("url") or not r.get("doc_type")]
        return {"ok": len(bad) == 0, "accepted": len(records) - len(bad), "rejected": len(bad)}

    def normalize(self, records: list[dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
        out = []
        for r in records:
            out.append(
                {
                    "ticker": str(r.get("ticker") or kwargs.get("entity") or "").upper(),
                    "doc_type": r.get("doc_type"),
                    "title": r.get("title") or r.get("anchor") or "",
                    "url": r.get("url"),
                    "checksum": r.get("checksum"),
                    "published_at": r.get("published_at"),
                    "archived_path": r.get("archived_path"),
                    "source": "ir_discovery",
                    "history": r.get("history") or [],
                }
            )
        return out

    def store(self, records: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        from live_data import store as lidi_store

        entity = str(kwargs.get("entity") or (records[0].get("ticker") if records else "")).upper()
        prior = (lidi_store.get_object("company_ir", entity) or {})
        prior_docs = list(prior.get("documents") or [])
        by_url = {d.get("url"): d for d in prior_docs if d.get("url")}
        for r in records:
            url = r.get("url")
            if not url:
                continue
            old = by_url.get(url) or {}
            hist = list(old.get("history") or [])
            hist.append({"seen_at": datetime.now(timezone.utc).isoformat(), "title": r.get("title")})
            by_url[url] = {**old, **r, "history": hist[-20:]}
        payload = {
            "ticker": entity,
            "documents": list(by_url.values()),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(by_url),
        }
        lidi_store.put_object("company_ir", entity, payload)
        return {"documents": len(by_url), "entity": entity}

    def coverage(self, **kwargs: Any) -> dict[str, Any]:
        from live_data import store as lidi_store
        from knowledge_factory.historical_depth.universe_priority import supported_universe

        u = kwargs.get("entities") or supported_universe()
        n = len(u) or 1
        covered = 0
        for e in u:
            docs = (lidi_store.get_object("company_ir", e) or {}).get("documents") or []
            if docs:
                covered += 1
        return {"connector_id": self.connector_id, "coverage_pct": round(100.0 * covered / n, 1), "covered": covered, "universe": n}

    # --- discovery pipeline ---------------------------------------------------

    def discover_hubs(self, entity: str) -> list[str]:
        hubs: list[str] = []
        if entity in SEED_HUBS:
            hubs.append(SEED_HUBS[entity])
        # Learned hubs from prior runs
        try:
            from live_data import store as lidi_store

            learned = (lidi_store.get_object("ir_hubs", entity) or {}).get("hubs") or []
            hubs.extend(str(h) for h in learned)
        except Exception:
            pass
        # Exchange corporate pages as discovery seeds
        hubs.append(DISCOVERY_TEMPLATES[0].format(symbol=entity))
        hubs.append(DISCOVERY_TEMPLATES[1].format(symbol_l=entity.lower()))
        # Common IR URL guesses from company name patterns
        for guess in (
            f"https://www.{entity.lower()}.com/investors",
            f"https://www.{entity.lower()}.com/investor-relations",
            f"https://{entity.lower()}.com/investors",
        ):
            if guess not in hubs:
                hubs.append(guess)
        # Dedup preserve order
        seen = set()
        out = []
        for h in hubs:
            if h not in seen:
                seen.add(h)
                out.append(h)
        return out

    def identify_documents(self, pages: list[tuple[str, bytes]], *, ticker: str) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for base, html in pages:
            try:
                text = html.decode("utf-8", errors="replace")
            except Exception:
                continue
            parser = _LinkParser()
            try:
                parser.feed(text)
            except Exception:
                continue
            for href, anchor in parser.links:
                url = urljoin(base, href)
                low = (url + " " + anchor).lower()
                if not any(url.lower().endswith(ext) for ext in DOC_EXT) and "pdf" not in low:
                    # Still classify IR HTML deep-links that look like report hubs
                    if not any(k in low for k in ("annual", "transcript", "presentation", "investor", "quarterly", "esg")):
                        continue
                doc_type = self.classify(anchor, url)
                if not doc_type:
                    continue
                docs.append(
                    {
                        "ticker": ticker,
                        "doc_type": doc_type,
                        "title": anchor or urlparse(url).path.split("/")[-1],
                        "anchor": anchor,
                        "url": url,
                        "checksum": hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
                        "discovered_from": base,
                        "published_at": None,
                    }
                )
            # Persist discovered IR hub if page had docs
            if docs:
                try:
                    from live_data import store as lidi_store

                    lidi_store.put_object(
                        "ir_hubs",
                        ticker,
                        {"hubs": [base], "updated_at": datetime.now(timezone.utc).isoformat()},
                    )
                except Exception:
                    pass
        return docs

    def classify(self, anchor: str, url: str) -> str | None:
        text = f"{anchor} {url}".lower()
        rules = (
            ("annual_report", ("annual report", "annual-report", "/ar/", "year-ended")),
            ("quarterly_report", ("quarterly result", "quarterly-result", "q1 ", "q2 ", "q3 ", "q4 ", "financial results")),
            ("investor_presentation", ("investor presentation", "investor-presentation", "earnings presentation")),
            ("corporate_presentation", ("corporate presentation", "company presentation")),
            ("earnings_transcript", ("transcript", "conference call", "earnings call")),
            ("esg_report", ("esg", "sustainability", "brsr")),
            ("governance_report", ("governance", "secretarial", "board report")),
            ("fact_sheet", ("fact sheet", "factsheet", "fact-sheet")),
            ("press_release", ("press release", "press-release", "media release")),
        )
        for doc_type, keys in rules:
            if any(k in text for k in keys):
                return doc_type
        if url.lower().endswith(".pdf") and "investor" in text:
            return "investor_presentation"
        return None

    def deduplicate(self, entity: str, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        out = []
        for d in docs:
            key = d.get("checksum") or d.get("url") or ""
            if key in seen:
                continue
            seen.add(key)
            out.append(d)
        return out

    def download_and_archive(self, entity: str, docs: list[dict[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
        from live_data import store as lidi_store
        from live_data.collectors.base import http_get

        archived = []
        for d in docs[:limit]:
            url = d.get("url")
            if not url or not any(url.lower().endswith(ext) for ext in DOC_EXT):
                continue
            try:
                raw = http_get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AGIB-LIDI/1.0)"}, timeout=45)
                checksum = hashlib.sha256(raw).hexdigest()
                name = re.sub(r"[^A-Za-z0-9._-]+", "_", urlparse(url).path.split("/")[-1] or "doc.bin")[:80]
                rec = lidi_store.put_raw_file(
                    "company_ir",
                    f"{entity}/{name}",
                    raw,
                    meta={"url": url, "doc_type": d.get("doc_type"), "checksum": checksum, "ticker": entity},
                )
                d["checksum"] = checksum
                d["archived_path"] = rec.get("path") if isinstance(rec, dict) else str(rec)
                archived.append(d)
                # Knowledge extract hook
                try:
                    from institutional_data.connectors.document_intel import extract_document_intelligence

                    extract_document_intelligence(entity, d, raw_bytes=raw if len(raw) < 2_000_000 else None)
                except Exception:
                    pass
            except Exception:
                continue
        return archived
