"""Processing Service — extract metadata, clean, section-aware prep for FRE."""

from __future__ import annotations

import re
import time
from typing import Any

from app.faa.authority import faa_authority
from app.faa.models import FetchedDocument
from app.fre.acquisition import acquire_from_text
from app.fre.models import FreDocument
from app.fre.parser import clean_text

_DATE_RE = re.compile(
    r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|[A-Z][a-z]{2,8}\s+\d{1,2},\s+20\d{2}|FY\s?\d{2,4}|Q[1-4]\s?FY\s?\d{2,4})\b"
)
_PAGE_RE = re.compile(r"\[page\s+(\d+)\]", re.I)
_TABLE_RE = re.compile(
    r"(?is)((?:consolidated|standalone)?\s*(?:balance sheet|profit and loss|cash flow|income statement|"
    r"financial statements?)[\s\S]{20,4000}?)(?=\n\[page|\n[A-Z][A-Z ]{8,}|\Z)"
)
_FOOTNOTE_RE = re.compile(r"(?m)^\s*(?:\*|†|‡|\d+)\s+.{10,200}$")


class ProcessingService:
    def __init__(self) -> None:
        self._parse_samples: list[float] = []

    def process(self, fetched: list[FetchedDocument]) -> list[FreDocument]:
        out: list[FreDocument] = []
        for item in fetched:
            t0 = time.perf_counter()
            try:
                doc = self._process_one(item)
                if doc:
                    out.append(doc)
            except Exception:
                continue
            finally:
                self._parse_samples.append((time.perf_counter() - t0) * 1000)
                self._parse_samples = self._parse_samples[-200:]
        return out

    def _process_one(self, item: FetchedDocument) -> FreDocument | None:
        if item.skipped or item.error or not (item.content_text or "").strip():
            return None
        cleaned = clean_text(item.content_text)
        cleaned = self._strip_noise(cleaned)
        if not cleaned:
            return None

        headings = self._extract_headings(cleaned)
        sections = self._extract_sections(cleaned, headings)
        pages = [int(p) for p in _PAGE_RE.findall(cleaned)]
        tables = [t.strip()[:500] for t in _TABLE_RE.findall(cleaned)[:5]]
        footnotes = [f.strip() for f in _FOOTNOTE_RE.findall(cleaned)[:20]]
        period = None
        m = _DATE_RE.search(cleaned[:2000]) or _DATE_RE.search(item.title or "")
        if m:
            period = m.group(0)

        meta_auth = (item.metadata or {}).get("authority")
        override = None
        if meta_auth is not None:
            try:
                override = int(meta_auth)
            except Exception:
                override = None
        auth = faa_authority(
            item.document_type,
            item.connector_id,
            organisation=item.organisation,
            override=override,
        )

        # Preserve tables/financial blocks as indivisible units for downstream chunking
        protected = cleaned
        for i, table in enumerate(tables):
            if table and table in protected:
                protected = protected.replace(table, f"\n<<<TABLE_BLOCK_{i}>>>\n{table}\n<<<END_TABLE_BLOCK_{i}>>>\n", 1)

        doc = acquire_from_text(
            title=item.title,
            text=protected,
            url=item.url,
            source=item.connector_id,
            document_type=item.document_type,
            company=item.company,
            symbol=item.symbol,
            published_at=item.published_at or period,
            organisation=item.organisation,
        )
        doc.checksum = item.checksum or doc.checksum
        doc.content_type = item.content_type
        doc.authority = auth
        doc.financial_year = period if period and "FY" in period.upper() else doc.financial_year
        doc.quarter = period if period and period.upper().startswith("Q") else doc.quarter
        doc.metadata = {
            **(doc.metadata or {}),
            "faa_fetch_id": item.fetch_id,
            "faa_live_fetch": item.live_fetch,
            "faa_connector": item.connector_id,
            "faa_retrieved_at": item.fetched_at.isoformat() if item.fetched_at else None,
            "etag": item.etag,
            "last_modified": item.last_modified,
            "fetch_ms": item.fetch_ms,
            "headings": headings[:20],
            "sections": sections[:30],
            "page_numbers": pages[:80],
            "tables_detected": len(tables),
            "footnotes": footnotes[:15],
            "reporting_period": period,
            "detected_content_type": item.content_type,
            "chunk_hints": {
                "target_tokens": [500, 1000],
                "never_split": ["table", "financial_statement"],
                "retain": ["company", "page", "heading", "section", "date", "source", "connector"],
            },
            "validation_status": "ok",
            **(item.metadata or {}),
        }
        return doc

    def _strip_noise(self, text: str) -> str:
        lines = []
        for line in text.splitlines():
            low = line.lower().strip()
            if not low:
                continue
            if any(
                x in low
                for x in (
                    "cookie",
                    "accept all",
                    "subscribe to our newsletter",
                    "sign in",
                    "log in",
                    "advertisement",
                    "sponsored content",
                    "enable javascript",
                )
            ):
                continue
            lines.append(line)
        # collapse duplicate consecutive paragraphs
        out = []
        prev = None
        for line in lines:
            if line == prev:
                continue
            out.append(line)
            prev = line
        return "\n".join(out)

    def _extract_headings(self, text: str) -> list[str]:
        heads = []
        for line in text.splitlines():
            s = line.strip()
            if 3 <= len(s) <= 80 and (
                s.isupper()
                or s.istitle()
                or s.endswith(":")
                or any(k in s.lower() for k in ("highlight", "result", "guidance", "risk", "outlook", "financial"))
            ):
                heads.append(s.rstrip(":"))
            if len(heads) >= 20:
                break
        return heads

    def _extract_sections(self, text: str, headings: list[str]) -> list[dict[str, Any]]:
        if not headings:
            return [{"heading": "body", "chars": len(text)}]
        sections: list[dict[str, Any]] = []
        for i, heading in enumerate(headings):
            start = text.find(heading)
            if start < 0:
                continue
            end = len(text)
            for nxt in headings[i + 1 :]:
                pos = text.find(nxt, start + len(heading))
                if pos > start:
                    end = pos
                    break
            chunk = text[start:end]
            page_m = _PAGE_RE.search(chunk)
            sections.append(
                {
                    "heading": heading,
                    "chars": len(chunk),
                    "page": int(page_m.group(1)) if page_m else None,
                }
            )
        return sections

    @property
    def avg_parse_ms(self) -> float:
        if not self._parse_samples:
            return 0.0
        return sum(self._parse_samples) / len(self._parse_samples)
