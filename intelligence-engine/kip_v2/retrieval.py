"""Module 9 — Knowledge Retrieval.

Answers a user question by searching, in order:
    1. Structured knowledge (Fact keyword/category match) — highest trust.
    2. Executive Summary sections built from that structured knowledge.
    3. Paragraph-level embedding similarity search (Module 1 evidence index)
       — used only as a fallback when structured knowledge has no match.

This module never re-runs extraction and never fabricates: if nothing
clears the confidence floor, it returns ``unknown: True`` instead of a best
guess (Core Principle 6).
"""

from __future__ import annotations

from typing import Any, Optional

from kip_v2.embeddings import Embedder, cosine_similarity, get_default_embedder, tokenize
from kip_v2.schema import FINANCIAL_METRICS, KNOWLEDGE_CATEGORIES, MANAGEMENT_TOPICS
from kip_v2.storage.base import KnowledgeStore

_UNKNOWN_CONFIDENCE_FLOOR = 0.35

_STOPWORDS = {
    "what", "is", "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "at",
    "was", "were", "are", "be", "been", "this", "that", "with", "as", "it", "its",
    "do", "does", "did", "how", "why", "when", "where", "who", "which", "tell", "me",
    "about", "please", "can", "you", "will", "shall", "has", "have", "had",
}

_ALL_KEYS = set(KNOWLEDGE_CATEGORIES) | set(FINANCIAL_METRICS) | set(MANAGEMENT_TOPICS)

_KEY_ALIASES: dict[str, str] = {
    "profit": "pat",
    "net profit": "pat",
    "sales": "revenue",
    "turnover": "revenue",
    "earnings": "eps",
    "margin": "ebitda_margin",
    "guidance": "strategy",
    "outlook": "strategy",
}


def _match_keys(question: str) -> list[str]:
    low = question.lower()
    matches = [key for key in _ALL_KEYS if key.replace("_", " ") in low]
    for alias, canonical in _KEY_ALIASES.items():
        if alias in low and canonical not in matches:
            matches.append(canonical)
    return matches


def _structured_search(store: KnowledgeStore, company_id: str, question: str) -> Optional[dict[str, Any]]:
    keys = _match_keys(question)
    if not keys:
        return None
    best = None
    for key in keys:
        facts = store.get_facts(company_id, key=key) or store.get_facts(company_id, category=key)
        for fact in facts:
            if best is None or fact.confidence > best.confidence:
                best = fact
    if best is None:
        return None
    return {
        "answer": best.value,
        "category": best.category,
        "key": best.key,
        "period": best.period,
        "confidence": best.confidence,
        "evidence": [
            {
                "document_id": best.evidence.document_id,
                "page": best.evidence.page,
                "snippet": best.evidence.snippet,
                "evidence_hash": best.evidence.evidence_hash,
            }
        ],
        "source": "structured_knowledge",
        "unknown": False,
    }


def _embedding_fallback_search(
    store: KnowledgeStore, company_id: str, question: str, embedder: Embedder, top_k: int = 3
) -> Optional[dict[str, Any]]:
    paragraphs = store.all_paragraphs(company_id)
    if not paragraphs:
        return None
    q_tokens = {t for t in tokenize(question) if t not in _STOPWORDS and len(t) > 2}
    if not q_tokens:
        return None
    q_vec = embedder.embed(question)
    scored = []
    for paragraph in paragraphs:
        p_tokens = {t for t in tokenize(paragraph.text) if t not in _STOPWORDS}
        overlap = len(q_tokens & p_tokens)
        if overlap == 0 and cosine_similarity(q_vec, paragraph.embedding) < 0.2:
            continue
        score = cosine_similarity(q_vec, paragraph.embedding) + 0.12 * overlap
        scored.append((score, paragraph))
    if not scored:
        return None
    scored.sort(key=lambda t: t[0], reverse=True)
    top_score, top_paragraph = scored[0]
    confidence = round(min(0.7, max(0.0, top_score)), 3)
    if confidence < _UNKNOWN_CONFIDENCE_FLOOR:
        return None
    return {
        "answer": top_paragraph.text,
        "category": "paragraph_evidence",
        "key": top_paragraph.section,
        "period": None,
        "confidence": confidence,
        "evidence": [
            {
                "document_id": top_paragraph.document_id,
                "page": top_paragraph.page,
                "snippet": top_paragraph.text[:500],
                "evidence_hash": top_paragraph.evidence_hash,
            }
        ],
        "source": "paragraph_embedding_fallback",
        "unknown": False,
    }


def answer_question(
    store: KnowledgeStore, company_id: str, question: str, embedder: Optional[Embedder] = None
) -> dict[str, Any]:
    embedder = embedder or get_default_embedder()

    result = _structured_search(store, company_id, question)
    if result is not None:
        return result

    result = _embedding_fallback_search(store, company_id, question, embedder)
    if result is not None:
        return result

    return {
        "answer": None,
        "confidence": 0.0,
        "evidence": [],
        "source": None,
        "unknown": True,
        "reason": "no_evidence_backed_knowledge_found",
    }
