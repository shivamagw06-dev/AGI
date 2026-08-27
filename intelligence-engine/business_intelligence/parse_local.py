"""Local official-document section parse/chunk — mirrors IDI labels without importing KF root."""

from __future__ import annotations

import hashlib
import re
from typing import Any

# Same heading → label map as IDI parsers/sections.py (extraction only).
# Headings must be short title lines — not content that merely starts with the phrase.
_SECTION_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*(management discussion(?: and analysis)?|md&a|management.s discussion)\s*:?\s*$", re.I), "MANAGEMENT_DISCUSSION"),
    (re.compile(r"^\s*(financial statements|consolidated statements|standalone statements)\s*:?\s*$", re.I), "FINANCIAL_STATEMENTS"),
    (re.compile(r"^\s*(notes to (the )?accounts|notes to financial statements|accounting notes)\s*:?\s*$", re.I), "NOTES"),
    (re.compile(r"^\s*(risk factors|key risks|risk disclosures)\s*:?\s*$", re.I), "RISK_FACTORS"),
    (re.compile(r"^\s*(capital allocation|capital expenditure|capex)\s*:?\s*$", re.I), "CAPITAL_ALLOCATION"),
    (re.compile(r"^\s*(business segments|segment (information|report|performance)|operating segments)\s*:?\s*$", re.I), "BUSINESS_SEGMENTS"),
    (re.compile(r"^\s*(guidance|outlook|forward.?looking)\s*:?\s*$", re.I), "GUIDANCE"),
    (re.compile(r"^\s*(strategy|strategic priorities|business strategy)\s*:?\s*$", re.I), "STRATEGY"),
    (re.compile(r"^\s*(table\s*\d+|financial table)\b.*$", re.I), "TABLES"),
    (re.compile(r"^\s*(business overview|products and services|corporate governance(?: report)?)\s*:?\s*$", re.I), "OTHER"),
]


def parse_document_text(doc: dict[str, Any]) -> dict[str, Any]:
    text = doc.get("text") or ""
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    current_label = "OTHER"
    current_heading = "Preamble"
    current_lines: list[str] = []
    page = 1
    chars = 0
    para_idx = 0

    def _flush() -> None:
        nonlocal para_idx
        body = "\n".join(current_lines).strip()
        if not body:
            return
        para_idx += 1
        sections.append(
            {
                "section": current_label,
                "heading": current_heading,
                "page": page,
                "paragraph": para_idx,
                "text": body,
                "char_count": len(body),
            }
        )

    for line in lines:
        chars += len(line) + 1
        if chars > page * 3000:
            page += 1
        matched = None
        for pat, label in _SECTION_MAP:
            if pat.search(line.strip()):
                matched = (label, line.strip())
                break
        if matched:
            _flush()
            current_label, current_heading = matched
            current_lines = []
            continue
        current_lines.append(line)
    _flush()

    return {
        "document_id": doc.get("document_id"),
        "parser": "fire03_local_section_parser_v1",
        "section_count": len(sections),
        "sections": sections,
        "pages": int(doc.get("pages") or page),
        "extracted_labels": sorted({s["section"] for s in sections}),
        "interpretation": False,
        "summarisation": False,
        "fabricated": False,
    }


def chunk_parsed_local(
    doc: dict[str, Any],
    parsed: dict[str, Any],
    *,
    max_chars: int = 1200,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    doc_id = str(doc["document_id"])
    for i, sec in enumerate(parsed.get("sections") or []):
        text = str(sec.get("text") or "").strip()
        if not text:
            continue
        parts = _split(text, max_chars)
        for j, part in enumerate(parts):
            chunk_id = f"{doc_id}_c{i:03d}_{j:02d}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "company": doc.get("company"),
                    "document_type": doc.get("type"),
                    "section": sec.get("section"),
                    "page": sec.get("page"),
                    "paragraph": sec.get("paragraph"),
                    "heading": sec.get("heading"),
                    "text": part,
                    "checksum": hashlib.sha1(part.encode("utf-8")).hexdigest()[:16],
                    "available_from": doc.get("available_from"),
                    "fabricated": False,
                }
            )
    return chunks


def _split(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            cut = text.rfind("\n\n", start, end)
            if cut <= start:
                cut = text.rfind(". ", start, end)
            if cut > start:
                end = cut + 1
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if p]
