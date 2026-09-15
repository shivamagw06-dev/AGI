"""BusinessFact builder — structured disclosure evidence, not summaries."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from business_intelligence.fkb_link import fkb_refs_for_category, resolve_fkb_refs
from business_intelligence.schema import (
    CONF_HIGH,
    CONF_LOW,
    CONF_MEDIUM,
    DOC_TYPE_PRIORITY,
    SECTION_CONFIDENCE,
)


def _sentence_around(text: str, start: int, end: int, *, max_len: int = 280) -> str:
    if not text:
        return ""
    left = text.rfind(".", 0, start)
    left = 0 if left < 0 else left + 1
    right = text.find(".", end)
    right = len(text) if right < 0 else right + 1
    excerpt = text[left:right].strip()
    if len(excerpt) > max_len:
        excerpt = excerpt[: max_len - 1].rstrip() + "…"
    return excerpt or text[max(0, start - 40) : min(len(text), end + 40)].strip()


def confidence_for(
    *,
    doc_type: str | None,
    section: str | None,
    explicit: bool = True,
) -> str:
    base = SECTION_CONFIDENCE.get(str(section or "OTHER"), CONF_LOW)
    dtype = str(doc_type or "")
    pri = DOC_TYPE_PRIORITY.get(dtype, 99)
    if not explicit:
        return CONF_LOW
    if pri <= 2 and base == CONF_HIGH:
        return CONF_HIGH
    if pri <= 5 and base in {CONF_HIGH, CONF_MEDIUM}:
        return CONF_HIGH if base == CONF_HIGH else CONF_MEDIUM
    if pri <= 8:
        return CONF_MEDIUM if base != CONF_LOW else CONF_LOW
    return CONF_LOW


def make_fact(
    *,
    category: str,
    statement: str,
    evidence: str,
    page: int | None,
    section: str | None,
    document: str | None,
    document_id: str | None = None,
    document_type: str | None = None,
    reporting_period: str | None = None,
    source: str | None = None,
    confidence: str | None = None,
    fkb_hints: list[str] | None = None,
    chunk_id: str | None = None,
    heading: str | None = None,
) -> dict[str, Any]:
    stmt = re.sub(r"\s+", " ", (statement or "").strip())
    evid = re.sub(r"\s+", " ", (evidence or "").strip())
    conf = confidence or confidence_for(doc_type=document_type, section=section, explicit=bool(evid))
    if conf not in {CONF_HIGH, CONF_MEDIUM, CONF_LOW}:
        conf = CONF_LOW
    hints = list(fkb_hints or []) + [category, stmt]
    refs = resolve_fkb_refs(*hints) or fkb_refs_for_category(category)
    fact_key = hashlib.sha1(
        f"{category}|{stmt}|{document_id}|{page}|{section}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "fact_id": f"bf:{fact_key}",
        "category": category,
        "statement": stmt,
        "evidence": evid,
        "page": page,
        "section": section,
        "heading": heading,
        "document": document,
        "document_id": document_id,
        "document_type": document_type,
        "source": source or document,
        "reporting_period": reporting_period,
        "confidence": conf,
        "chunk_id": chunk_id,
        "fkb_refs": refs,
        "fabricated": False,
        "inferred": False,
        "recommendation": None,
    }


def fact_from_match(
    *,
    category: str,
    statement: str,
    text: str,
    match: re.Match[str] | None,
    chunk: dict[str, Any],
    document: dict[str, Any],
    reporting_period: str | None,
    fkb_hints: list[str] | None = None,
) -> dict[str, Any]:
    if match is not None:
        evid = _sentence_around(text, match.start(), match.end())
    else:
        evid = (text or "")[:280].strip()
    return make_fact(
        category=category,
        statement=statement,
        evidence=evid,
        page=chunk.get("page"),
        section=chunk.get("section"),
        heading=chunk.get("heading"),
        document=document.get("title") or document.get("type"),
        document_id=document.get("document_id"),
        document_type=document.get("type") or chunk.get("document_type"),
        reporting_period=reporting_period,
        source=document.get("source") or document.get("title"),
        chunk_id=chunk.get("chunk_id"),
        fkb_hints=fkb_hints,
    )


def dedupe_facts(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for f in facts:
        key = f"{f.get('category')}|{(f.get('statement') or '').lower()}|{f.get('document_id')}|{f.get('page')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def confidence_distribution(facts: list[dict[str, Any]]) -> dict[str, int]:
    dist = {CONF_HIGH: 0, CONF_MEDIUM: 0, CONF_LOW: 0}
    for f in facts:
        c = f.get("confidence") or CONF_LOW
        dist[c] = dist.get(c, 0) + 1
    return dist
