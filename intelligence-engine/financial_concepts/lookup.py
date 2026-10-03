"""Concept lookup — exact key, alias, and natural-language question matching.

Mirrors financial_foundations.education's proven matching approach (exact
key -> alias -> "all component words present" -> substring) so the same
question-answering reliability that already works for Phase 1 concepts
extends to Phase 2.6's much larger vocabulary.
"""

from __future__ import annotations

import re

from financial_concepts.concepts import ALL_CONCEPTS, get_concept
from financial_concepts.schema import ConceptCard

_STOPWORDS = {
    "a", "an", "the", "to", "for", "of", "in", "on", "is", "are", "what",
    "why", "how", "explain", "describe", "define", "does", "do", "and",
}

# Common abbreviations / phrasings that don't tokenize cleanly to their key.
ALIASES: dict[str, str] = {
    "eva": "eva",
    "roic": "roic",
    "roe": "roe_decomposition",
    "roa": "roa_decomposition",
    "roce": "roce",
    "wacc": "wacc",
    "capm": "cost_of_equity",
    "dcf": "dcf",
    "lbo": "lbo",
    "sotp": "sotp",
    "peg": "peg",
    "peg ratio": "peg",
    "p e": "p_e",
    "p e ratio": "p_e",
    "price to earnings": "p_e",
    "p b": "p_b",
    "p b ratio": "p_b",
    "price to book": "p_b",
    "ev ebitda": "ev_ebitda",
    "ev sales": "ev_sales",
    "ev": "enterprise_value",
    "enterprise value": "enterprise_value",
    "market cap": "market_capitalization",
    "nopat": "nopat",
    "nim": "nim",
    "casa": "casa",
    "gnpa": "gnpa",
    "nnpa": "nnpa",
    "cet1": "cet1",
    "rwa": "risk_weighted_assets",
    "dupont": "dupont_model",
    "dupont model": "dupont_model",
    "dupont analysis": "dupont_model",
    "fcf": "free_cash_flow",
    "fcf yield": "fcf_yield",
    "free cash flow yield": "fcf_yield",
    "irr": "irr",
    "npv": "npv",
    "tam": "total_addressable_market",
    "sam": "serviceable_addressable_market",
    "dscr": "debt_service_coverage",
    "emh": "efficient_market_hypothesis",
    "efficient market hypothesis": "efficient_market_hypothesis",
    "moat": "economic_moat",
    "economic moat": "economic_moat",
    "network effect": "network_effect",
    "network effects": "network_effect",
    "switching cost": "switching_cost",
    "switching costs": "switching_cost",
    "pricing power": "pricing_power",
    "ltv": "customer_lifetime_value",
    "cac": "customer_lifetime_value",
    "croci": "croci",
    "rote": "rote",
    "qip": "qip",
    "free cash flow yield": "fcf_yield",
    "unlevered free cash flow": "unlevered_fcf",
    "levered free cash flow": "levered_fcf",
    "fcff": "unlevered_fcf",
    "fcfe": "levered_fcf",
    "capital allocation": "capital_recycling",
    "gross margin": "contribution_margin",
}


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", (text or "").strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _phrase_in(phrase: str, cleaned: str) -> bool:
    """Whole-phrase match — prevents alias 'ev' matching inside 'every'."""
    if not phrase or not cleaned:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", cleaned) is not None


def _all_words_present(key: str, words: set[str]) -> bool:
    parts = [w for w in key.replace("-", "_").split("_") if w and w not in _STOPWORDS]
    return bool(parts) and all(w in words for w in parts)


def explain(topic: str) -> dict:
    """Single entry point: exact key -> alias -> keyword match -> not found."""

    raw = topic or ""
    cleaned = _normalize(raw)
    if not cleaned:
        return {"found": False, "topic": topic}

    topic_key = cleaned.replace(" ", "_")

    card = get_concept(topic_key)
    if card:
        return {"found": True, **card.to_dict()}

    if cleaned in ALIASES:
        card = get_concept(ALIASES[cleaned])
        if card:
            return {"found": True, **card.to_dict()}

    words = set(cleaned.split())
    stripped_words = words - _STOPWORDS

    # Longest-matching-phrase-wins: pool every library key phrase AND every
    # alias phrase together, keep only those that are literal substrings of
    # the cleaned question, and pick the LONGEST match. This is what makes
    # "Levered Free Cash Flow" resolve to levered_fcf (an alias phrase)
    # rather than the shorter, also-present "free cash flow" substring
    # (free_cash_flow's own key phrase) — specificity beats an arbitrary
    # key/alias tier ordering. A fixed tier order previously let a shorter
    # substring match (e.g. plain "roic") win over a more specific,
    # equally-present phrase (e.g. "incremental roic") purely because of
    # which list it was checked in first.
    candidates: list[tuple[int, str]] = []  # (phrase_length, key)
    for key in ALL_CONCEPTS:
        key_phrase = key.replace("_", " ")
        if _phrase_in(key_phrase, cleaned):
            candidates.append((len(key_phrase), key))
    for phrase, key in ALIASES.items():
        if _phrase_in(phrase, cleaned):
            candidates.append((len(phrase), key))
    if candidates:
        candidates.sort(key=lambda t: t[0], reverse=True)
        card = get_concept(candidates[0][1])
        if card:
            return {"found": True, **card.to_dict()}

    # Alias by word-subset (handles aliases whose words appear out of
    # order or are not a literal contiguous substring).
    for phrase, key in sorted(ALIASES.items(), key=lambda kv: len(kv[0]), reverse=True):
        phrase_words = set(phrase.split())
        if phrase_words and phrase_words <= words:
            card = get_concept(key)
            if card:
                return {"found": True, **card.to_dict()}

    # Loosest fallback: every component word of a key present, order-independent.
    for key in sorted(ALL_CONCEPTS, key=len, reverse=True):
        if _all_words_present(key, stripped_words):
            card = get_concept(key)
            if card:
                return {"found": True, **card.to_dict()}

    return {"found": False, "topic": topic}


def search(query: str, limit: int = 5) -> list[dict]:
    """Ranked multi-result search — used by the /search API and by the
    exam grader to check whether an answer touches the right concepts."""

    cleaned = _normalize(query)
    if not cleaned:
        return []
    words = set(cleaned.split()) - _STOPWORDS
    scored: list[tuple[int, ConceptCard]] = []
    for key, card in ALL_CONCEPTS.items():
        haystack = _normalize(f"{card.title} {card.definition} {card.business_meaning}")
        hit_words = len(words & set(haystack.split()))
        key_phrase_hit = 2 if key.replace("_", " ") in cleaned else 0
        score = hit_words + key_phrase_hit
        if score > 0:
            scored.append((score, card))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [c.to_dict() for _, c in scored[:limit]]
