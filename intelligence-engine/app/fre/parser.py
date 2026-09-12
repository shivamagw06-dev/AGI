"""Steps 5–6 — Document parse + clean."""

from __future__ import annotations

import re
from typing import Any

from app.fre.models import FreDocument

_NAV_NOISE = re.compile(
    r"(?i)(cookie(s)?\s+(policy|settings)|accept all cookies|subscribe to newsletter|"
    r"sign in|log in|menu|home\s*\|\s*about|advertisement|sponsored content)"
)
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")
_HEADER_FOOTER = re.compile(r"(?m)^(page\s+\d+\s+of\s+\d+|confidential|all rights reserved).*$", re.I)


def clean_text(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        if _NAV_NOISE.search(line):
            continue
        line = _HEADER_FOOTER.sub("", line)
        line = _MULTI_SPACE.sub(" ", line).strip()
        if line:
            lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = _MULTI_NL.sub("\n\n", cleaned).strip()
    # de-duplicate consecutive paragraphs
    paras = []
    for p in cleaned.split("\n\n"):
        if not paras or paras[-1] != p:
            paras.append(p)
    return "\n\n".join(paras)


def parse_document(doc: FreDocument) -> dict[str, Any]:
    cleaned = clean_text(doc.raw_text)
    headings = []
    for line in cleaned.splitlines():
        if len(line) < 80 and (
            line.endswith(":")
            or line.istitle()
            or line.isupper()
            or any(k in line.lower() for k in ("highlights", "guidance", "risks", "outlook", "results"))
        ):
            headings.append(line.rstrip(":"))
    sections = []
    current = {"heading": "Body", "text": []}
    for line in cleaned.splitlines():
        if line in headings:
            if current["text"]:
                sections.append({"heading": current["heading"], "text": "\n".join(current["text"])})
            current = {"heading": line, "text": []}
        else:
            current["text"].append(line)
    if current["text"]:
        sections.append({"heading": current["heading"], "text": "\n".join(current["text"])})

    doc.raw_text = cleaned
    doc.ensure_checksum()
    return {
        "document_id": doc.document_id,
        "title": doc.title,
        "publication_date": doc.published_at,
        "author": doc.author,
        "organisation": doc.organisation,
        "company": doc.company,
        "financial_year": doc.financial_year,
        "quarter": doc.quarter,
        "headings": headings,
        "sections": sections,
        "tables": [],  # reserved — never split tables in chunker
        "page_estimate": max(1, len(cleaned) // 1800),
    }
