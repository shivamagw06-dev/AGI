"""Module 4 — Management Intelligence.

Extracts attributed management commentary from conference-call transcripts,
investor presentations, and MD&A narrative. Every statement is stored with
quote, speaker, topic, sentiment, confidence and page — never freeform LLM
paraphrase.

Two deterministic extraction patterns are supported:
    1. Transcript "speaker line" format: ``Name (Title): statement text``
    2. Reported/quoted speech: ``"...quote..." said Name, Title``
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from kip_v2.schema import Evidence, Fact, MANAGEMENT_TOPICS, Paragraph

TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "growth_priorities": ("growth priorit", "our priority is to grow", "focus area for growth"),
    "expansion": ("expansion", "new capacity", "new plant", "entering new markets", "scaling up"),
    "demand_outlook": ("demand outlook", "demand environment", "demand remains", "order book"),
    "pricing": ("pricing", "price increase", "price hike", "realizations"),
    "margin_expectations": ("margin expectation", "margin guidance", "margin outlook", "margin trajectory"),
    "hiring": ("hiring", "headcount", "talent acquisition", "attrition"),
    "ai_strategy": (" ai ", "artificial intelligence", "generative ai", "automation strategy"),
    "capital_allocation": ("capital allocation", "capex guidance", "dividend policy", "buyback plan"),
}
assert set(TOPIC_KEYWORDS) == set(MANAGEMENT_TOPICS)

_POSITIVE_WORDS = (
    "strong", "robust", "healthy", "positive", "confident", "improve", "growth", "record",
    "resilient", "optimistic", "encouraging", "momentum", "accelerat",
)
_NEGATIVE_WORDS = (
    "weak", "decline", "challenge", "headwind", "pressure", "cautious", "muted", "slowdown",
    "concern", "uncertain", "soft demand", "de-grow",
)

_SPEAKER_LINE_RE = re.compile(
    r"^([A-Z][A-Za-z\.\-]+(?:\s+[A-Z][A-Za-z\.\-]+){0,3})\s*(?:\(([^)]+)\))?\s*:\s*(.{15,})$"
)
_QUOTE_RE = re.compile(r"[\u201c\"]([^\u201d\"]{15,400})[\u201d\"]")
_ATTRIBUTION_RE = re.compile(
    r"\b(?:said|stated|noted|added|remarked|commented)\s+([A-Z][A-Za-z\.\-]+(?:\s+[A-Z][A-Za-z\.\-]+){0,3})", re.I
)
_TITLE_KEYWORDS = ("chairman", "managing director", "ceo", "chief executive", "cfo", "chief financial",
                    "coo", "president", "executive director", "director", "head of")


def _score_sentiment(text: str) -> tuple[float, str]:
    low = text.lower()
    pos = sum(1 for w in _POSITIVE_WORDS if w in low)
    neg = sum(1 for w in _NEGATIVE_WORDS if w in low)
    if pos == neg == 0:
        return 0.0, "neutral"
    score = (pos - neg) / max(1, pos + neg)
    label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
    return round(score, 3), label


def _classify_topics(text: str) -> list[str]:
    low = text.lower()
    return [topic for topic, keywords in TOPIC_KEYWORDS.items() if any(kw in low for kw in keywords)]


def extract_statements_from_paragraph(paragraph: Paragraph) -> list[dict]:
    text = paragraph.text
    statements: list[dict] = []

    m = _SPEAKER_LINE_RE.match(text)
    if m:
        speaker, title, quote = m.group(1), m.group(2), m.group(3)
        is_plausible_speaker = bool(title) or any(t in (title or "").lower() for t in _TITLE_KEYWORDS) or len(speaker.split()) <= 4
        if is_plausible_speaker and len(quote) >= 15:
            topics = _classify_topics(quote)
            if topics:
                sentiment_score, sentiment_label = _score_sentiment(quote)
                for topic in topics:
                    statements.append(
                        {"quote": quote.strip(), "speaker": speaker.strip(), "title": title, "topic": topic,
                         "sentiment": sentiment_label, "sentiment_score": sentiment_score, "confidence": 0.8}
                    )

    if not statements:
        for qm in _QUOTE_RE.finditer(text):
            quote = qm.group(1)
            topics = _classify_topics(quote)
            if not topics:
                continue
            am = _ATTRIBUTION_RE.search(text)
            speaker = am.group(1).strip() if am else None
            sentiment_score, sentiment_label = _score_sentiment(quote)
            for topic in topics:
                statements.append(
                    {"quote": quote.strip(), "speaker": speaker, "title": None, "topic": topic,
                     "sentiment": sentiment_label, "sentiment_score": sentiment_score,
                     "confidence": 0.75 if speaker else 0.55}
                )

    return statements


def build_management_facts(
    company_id: str, paragraphs: Iterable[Paragraph], period: Optional[str] = None
) -> list[Fact]:
    facts: list[Fact] = []
    for paragraph in paragraphs:
        for stmt in extract_statements_from_paragraph(paragraph):
            evidence = Evidence(
                document_id=paragraph.document_id,
                page=paragraph.page,
                paragraph_id=paragraph.paragraph_id,
                snippet=paragraph.text[:500],
            )
            fact_id = Fact.make_id(company_id, "management_statement", stmt["topic"], period, evidence.evidence_hash)
            facts.append(
                Fact(
                    fact_id=fact_id,
                    company_id=company_id,
                    category="management_statement",
                    key=stmt["topic"],
                    value=stmt["quote"],
                    period=period,
                    unit=None,
                    currency=None,
                    confidence=stmt["confidence"],
                    evidence=evidence,
                    source_document_id=paragraph.document_id,
                    extra={
                        "speaker": stmt.get("speaker"),
                        "title": stmt.get("title"),
                        "sentiment": stmt.get("sentiment"),
                        "sentiment_score": stmt.get("sentiment_score"),
                    },
                )
            )
    return facts
