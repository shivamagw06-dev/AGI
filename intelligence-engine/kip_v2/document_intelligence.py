"""Module 1 — Document Intelligence Engine.

Pipeline: Document -> (OCR, external) -> Section Detection -> Paragraph
Segmentation -> Table Extraction -> Entity Recognition -> evidence-indexed
Paragraph records ready for the Knowledge Store.

Input is already-extracted plain text (OCR is an external ingestion-adapter
concern: feed the OCR'd text of a scanned document in exactly the same way as
a native-text document — this module never touches images/PDF bytes itself).
Page boundaries are recognised via a form-feed (``\\f``) or an explicit
``[PAGE n]`` marker; a document with neither is treated as a single page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from kip_v2.schema import Document, Paragraph, sha256_hex

# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

SECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("business_overview", re.compile(r"^\s*(business overview|about (the company|us)|our business)\s*$", re.I)),
    ("management_discussion", re.compile(r"^\s*management discussion (and|&) analysis\b", re.I)),
    ("risk_factors", re.compile(r"^\s*(risk factors?|risks? and concerns)\s*$", re.I)),
    ("segment_information", re.compile(r"^\s*(segment (information|results|performance)|business segments?)\s*$", re.I)),
    ("financial_statements", re.compile(r"^\s*(financial statements?|financial results?|financial highlights)\s*$", re.I)),
    ("corporate_governance", re.compile(r"^\s*corporate governance\b", re.I)),
    ("directors_report", re.compile(r"^\s*(directors'?|board'?s) report\b", re.I)),
    ("capital_allocation", re.compile(r"^\s*(capital allocation|dividend|capex plan)\b", re.I)),
    ("management_commentary", re.compile(r"^\s*(management commentary|earnings call|conference call|transcript)\b", re.I)),
    ("strategy_outlook", re.compile(r"^\s*(strategy|outlook|guidance|future plans?)\s*$", re.I)),
    ("esg", re.compile(r"^\s*(esg|sustainability|corporate social responsibility|csr)\b", re.I)),
    ("mna", re.compile(r"^\s*(mergers? (and|&) acquisitions?|acquisitions?|m ?& ?a)\b", re.I)),
    ("related_party", re.compile(r"^\s*related part(y|ies) (transactions?|disclosures?)\b", re.I)),
]

HEADING_HEURISTIC = re.compile(r"^[A-Z0-9][A-Za-z0-9 ,&'\-]{2,80}$")


def _looks_like_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 90:
        return False
    if s.endswith((".", ",", ";")):
        return False
    words = s.split()
    if len(words) > 12:
        return False
    upper_ratio = sum(1 for c in s if c.isupper()) / max(1, sum(1 for c in s if c.isalpha()))
    return bool(HEADING_HEURISTIC.match(s)) and (upper_ratio > 0.5 or s.istitle())


def detect_section(line: str) -> str | None:
    for section, pattern in SECTION_PATTERNS:
        if pattern.match(line.strip()):
            return section
    return None


# ---------------------------------------------------------------------------
# Table heuristic
# ---------------------------------------------------------------------------

_NUMERIC_TOKEN = re.compile(r"[\d,]+\.?\d*%?")


def _is_table_line(line: str) -> bool:
    if "\t" in line or "|" in line:
        return True
    tokens = line.split()
    numeric_tokens = sum(1 for t in tokens if _NUMERIC_TOKEN.fullmatch(t.strip(",")))
    return len(tokens) >= 4 and numeric_tokens >= 3


# ---------------------------------------------------------------------------
# Entity recognition (lightweight, deterministic dictionary + heuristic)
# ---------------------------------------------------------------------------

# A small default gazetteer; callers (e.g. entity_resolution) can pass a
# richer dictionary of {surface_form_lower: canonical_id} via known_entities.
_DEFAULT_TITLES = (
    "chairman", "managing director", "chief executive officer", "ceo", "cfo",
    "chief financial officer", "coo", "president", "executive director", "director",
)

_PROPER_NOUN_RUN = re.compile(r"\b([A-Z][a-zA-Z\.&]*(?:\s+[A-Z][a-zA-Z\.&]*){0,3})\b")
_STOPWORD_STARTS = {"The", "This", "That", "These", "Our", "We", "It", "In", "On", "For", "As", "A", "An"}


def recognize_entities(text: str, known_entities: dict[str, str] | None = None) -> list[str]:
    """Returns canonical entity ids/names mentioned in ``text``.

    Known entities (companies, tickers, executives) are matched first via the
    supplied dictionary (case-insensitive substring match). Any remaining
    capitalized multi-word proper-noun runs are returned as generic mentions
    prefixed ``mention:`` — these are NOT asserted to be resolved entities,
    just candidates for Module 6 to later resolve.
    """

    found: list[str] = []
    known_entities = known_entities or {}
    low = text.lower()
    for surface, canonical in known_entities.items():
        if surface.lower() in low and canonical not in found:
            found.append(canonical)

    for match in _PROPER_NOUN_RUN.finditer(text):
        phrase = match.group(1).strip()
        first_word = phrase.split()[0]
        if first_word in _STOPWORD_STARTS or len(phrase) < 4:
            continue
        if any(phrase.lower() in k.lower() or k.lower() in phrase.lower() for k in known_entities):
            continue
        tag = f"mention:{phrase}"
        if tag not in found:
            found.append(tag)
    return found[:25]


# ---------------------------------------------------------------------------
# Importance scoring
# ---------------------------------------------------------------------------

_IMPORTANT_KEYWORDS = (
    "revenue", "ebitda", "profit", "margin", "growth", "capex", "debt", "dividend",
    "guidance", "risk", "strategy", "acquisition", "buyback", "outlook", "demand",
    "capacity", "expansion", "cash flow",
)


def importance_score(text: str, section: str) -> float:
    score = 0.1
    low = text.lower()
    score += 0.04 * sum(1 for kw in _IMPORTANT_KEYWORDS if kw in low)
    if _NUMERIC_TOKEN.search(text):
        score += 0.15
    if section in ("financial_statements", "management_discussion", "risk_factors", "strategy_outlook", "capital_allocation"):
        score += 0.2
    length_bonus = min(0.15, len(text) / 2000.0)
    score += length_bonus
    return round(min(1.0, score), 4)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@dataclass
class DocumentIntelligenceResult:
    document: Document
    paragraphs: list[Paragraph]
    stats: dict


def _split_pages(text: str) -> list[str]:
    if "\f" in text:
        return text.split("\f")
    marker_split = re.split(r"\n\s*\[PAGE\s+\d+\]\s*\n", "\n" + text)
    if len(marker_split) > 1:
        return marker_split[1:]
    return [text]


def make_document_id(company_id: str, doc_type: str, period: str, source: str) -> str:
    return "doc_" + sha256_hex(company_id, doc_type, period, source)[:20]


def process_document(
    *,
    company_id: str,
    doc_type: str,
    period: str,
    title: str,
    source: str,
    text: str,
    document_id: str | None = None,
    published_at: str | None = None,
    known_entities: dict[str, str] | None = None,
    embedder=None,
) -> DocumentIntelligenceResult:
    """Runs the full Module 1 pipeline over already-extracted document text."""

    if embedder is None:
        from kip_v2.embeddings import get_default_embedder

        embedder = get_default_embedder()

    doc_id = document_id or make_document_id(company_id, doc_type, period, source)
    pages = _split_pages(text)
    paragraphs: list[Paragraph] = []
    current_section = "general"
    idx = 0
    tables_found = 0

    for page_no, page_text in enumerate(pages, start=1):
        blocks = re.split(r"\n\s*\n", page_text.strip())
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            lines = [ln for ln in block.splitlines() if ln.strip()]
            if len(lines) == 1 and _looks_like_heading(lines[0]):
                detected = detect_section(lines[0])
                current_section = detected or lines[0].strip().lower().replace(" ", "_")[:40]
                continue

            is_table = sum(1 for ln in lines if _is_table_line(ln)) >= max(1, len(lines) // 2)
            if is_table:
                tables_found += 1

            para_text = " ".join(ln.strip() for ln in lines)
            if len(para_text) < 6:
                continue

            entities = recognize_entities(para_text, known_entities)
            paragraph = Paragraph(
                paragraph_id=f"{doc_id}:p{idx}",
                document_id=doc_id,
                company_id=company_id,
                section=current_section,
                page=page_no,
                index=idx,
                text=para_text[:4000],
                is_table=is_table,
                entities=entities,
                importance_score=importance_score(para_text, current_section),
                embedding=embedder.embed(para_text),
            )
            paragraphs.append(paragraph)
            idx += 1

    document = Document(
        document_id=doc_id,
        company_id=company_id,
        doc_type=doc_type,
        period=period,
        title=title,
        source=source,
        page_count=len(pages),
        published_at=published_at,
    )

    stats = {
        "paragraphs": len(paragraphs),
        "pages": len(pages),
        "tables_detected": tables_found,
        "sections_detected": len({p.section for p in paragraphs}),
        "parse_success": True,
    }
    return DocumentIntelligenceResult(document=document, paragraphs=paragraphs, stats=stats)
