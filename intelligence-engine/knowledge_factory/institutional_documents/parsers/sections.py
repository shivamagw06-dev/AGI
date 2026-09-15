"""Structured section extraction — no interpretation, no summarisation."""

from __future__ import annotations

import re
from typing import Any

from knowledge_factory.institutional_documents.schema import PARSER_SECTIONS

# Heading patterns → canonical section labels (extraction only).
_SECTION_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*(management discussion|md&a|management.s discussion)", re.I), "MANAGEMENT_DISCUSSION"),
    (re.compile(r"^\s*(financial statements|consolidated statements|standalone statements)", re.I), "FINANCIAL_STATEMENTS"),
    (re.compile(r"^\s*(notes to (the )?accounts|notes to financial statements|accounting notes)", re.I), "NOTES"),
    (re.compile(r"^\s*(risk factors|key risks|risk disclosures)", re.I), "RISK_FACTORS"),
    (re.compile(r"^\s*(capital allocation|capital expenditure|capex)", re.I), "CAPITAL_ALLOCATION"),
    (re.compile(r"^\s*(business segments|segment (information|report|performance))", re.I), "BUSINESS_SEGMENTS"),
    (re.compile(r"^\s*(guidance|outlook|forward.?looking)", re.I), "GUIDANCE"),
    (re.compile(r"^\s*(strategy|strategic priorities|business strategy)", re.I), "STRATEGY"),
    (re.compile(r"^\s*(table\s*\d+|financial table)", re.I), "TABLES"),
]


def parse_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Parse plain-text institutional document into sections/tables markers."""
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
                "section": current_label if current_label in PARSER_SECTIONS else "OTHER",
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

    tables = [s for s in sections if s["section"] == "TABLES"]
    return {
        "document_id": doc.get("document_id"),
        "parser": "idi_section_parser_v1",
        "section_count": len(sections),
        "sections": sections,
        "tables": tables,
        "pages": int(doc.get("pages") or page),
        "extracted_labels": sorted({s["section"] for s in sections}),
        "interpretation": False,
        "summarisation": False,
        "fabricated": False,
    }
