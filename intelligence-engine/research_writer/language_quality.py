"""Language quality — scrub leaks, placeholders, gate spam; institutional phrasing."""

from __future__ import annotations

import re
from typing import Any

_INTERNAL = re.compile(
    r"\b(CID|LEO|IRP|DVC|ECP|SIF|FLE|MEE|AOI|EVE|IIE|KF|KIP|FAA|FRE|AIL|CAE|ICI|IAF|IRW|"
    r"Company Analysis|Financial Intelligence|MarketDataClient|Yahoo|Groww|IndianAPI|"
    r"AlphaVantage|TwelveData|Capital IQ|Finnhub|FMP|Polygon|provider|API|engine|"
    r"Academy|canonical model|framework identifier)\b",
    re.I,
)

_PLACEHOLDER = re.compile(
    r"\b(Unknown|N/?A|None listed|placeholder|TODO|TBD|null|undefined)\b|\u2014|\bMissing\b|: —",
    re.I,
)

_GRADE_SPAM = re.compile(
    r"(Coverage\s*\d+%|Knowledge Grade\s*[A-F][+\-]?|Research Grade\s*[A-F][+\-]?|"
    r"Data Grade\s*[A-F][+\-]?|Recommendation withheld)",
    re.I,
)

_SCORE_DUMP = re.compile(
    r"\b(Business Quality|Financial Quality|Management Score)\s*[:=]?\s*\d+(\.\d+)?\b",
    re.I,
)


def scrub_leaks(text: Any, *, limit: int = 1200) -> str:
    s = str(text or "").strip()
    if not s:
        return ""
    s = _INTERNAL.sub("institutional research", s)
    s = _GRADE_SPAM.sub(
        "Current institutional evidence is sufficient to assess the business, "
        "although additional financial history would further improve long-term conviction",
        s,
    )
    s = _SCORE_DUMP.sub("franchise quality remains under institutional review", s)
    s = _PLACEHOLDER.sub("", s)
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"\s+([,.])", r"\1", s).strip(" ,;")
    return s[:limit]


def is_placeholder(text: Any) -> bool:
    s = str(text or "").strip()
    if not s:
        return True
    if _PLACEHOLDER.fullmatch(s):
        return True
    if s in {"—", "-", "n/a", "N/A", "Unknown", "None", "null"}:
        return True
    return False


def natural_unavailable(topic: str = "this dimension") -> str:
    return (
        f"Evidence on {topic} remains incomplete in the current file; "
        "the assessment therefore relies on the broader institutional context rather than a single datapoint."
    )


def dedupe_paragraphs(paragraphs: list[str]) -> list[str]:
    """Repetition detector — drop near-duplicate ideas."""
    out: list[str] = []
    seen_norms: list[str] = []
    for p in paragraphs:
        clean = scrub_leaks(p, limit=800)
        if not clean or is_placeholder(clean):
            continue
        norm = re.sub(r"[^a-z0-9]+", " ", clean.lower()).strip()
        tokens = set(norm.split())
        duplicate = False
        for prev in seen_norms:
            prev_tokens = set(prev.split())
            if not tokens or not prev_tokens:
                continue
            overlap = len(tokens & prev_tokens) / max(1, len(tokens | prev_tokens))
            if overlap >= 0.72:
                duplicate = True
                break
        if duplicate:
            continue
        out.append(clean)
        seen_norms.append(norm)
    return out


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text or "") if w])


def clamp_words(text: str, *, min_words: int = 0, max_words: int = 150) -> str:
    words = [w for w in re.split(r"\s+", scrub_leaks(text, limit=4000)) if w]
    if len(words) > max_words:
        words = words[:max_words]
        text = " ".join(words)
        if not text.endswith("."):
            text = text.rstrip(",;") + "."
        return text
    if min_words and len(words) < min_words:
        return " ".join(words)
    return " ".join(words)
