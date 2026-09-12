"""Step 7 — Section-aware chunking (never split tables / financial statements)."""

from __future__ import annotations

import re
from typing import Any

from app.fre.models import FreChunk, FreDocument

_TOKENISH = re.compile(r"\S+")
_TABLE_GUARD = re.compile(r"(?i)\b(consolidated\s+financial\s+statements|balance\s+sheet|cash\s+flow\s+statement|profit\s+and\s+loss)\b")


def _tokens(text: str) -> int:
    return len(_TOKENISH.findall(text or ""))


def chunk_document(doc: FreDocument, parsed: dict[str, Any] | None = None, *, target_tokens: int = 750) -> list[FreChunk]:
    sections = (parsed or {}).get("sections") or [{"heading": "Body", "text": doc.raw_text}]
    chunks: list[FreChunk] = []
    page_est = int((parsed or {}).get("page_estimate") or 1)

    for idx, section in enumerate(sections):
        heading = str(section.get("heading") or "Body")
        text = str(section.get("text") or "").strip()
        if not text:
            continue
        # Keep financial statement blocks intact
        if _TABLE_GUARD.search(heading) or _TABLE_GUARD.search(text[:200]):
            parts = [text]
        else:
            parts = _split_to_target(text, target_tokens)

        for part in parts:
            tok = _tokens(part)
            chunks.append(
                FreChunk(
                    document_id=doc.document_id,
                    text=part,
                    heading=heading,
                    section=heading,
                    page=min(page_est, idx + 1),
                    company=doc.company,
                    symbol=doc.symbol,
                    document_type=doc.document_type,
                    source=doc.source,
                    published_at=doc.published_at,
                    reporting_period=doc.quarter or doc.financial_year,
                    region=doc.region,
                    language=doc.language,
                    authority=doc.authority,
                    confidence=0.75 if doc.authority >= 8 else 0.6,
                    token_estimate=tok,
                    metadata={
                        "title": doc.title,
                        "url": doc.url,
                        "organisation": doc.organisation,
                        "tier": doc.tier,
                    },
                )
            )
    return chunks


def _split_to_target(text: str, target: int) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paras:
        return [text]
    out: list[str] = []
    buf: list[str] = []
    count = 0
    for p in paras:
        t = _tokens(p)
        if buf and count + t > target and count >= int(target * 0.55):
            out.append("\n\n".join(buf))
            buf, count = [p], t
        else:
            buf.append(p)
            count += t
    if buf:
        out.append("\n\n".join(buf))
    return out
