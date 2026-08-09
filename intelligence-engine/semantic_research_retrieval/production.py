"""Ask AGI Semantic Research Retrieval V2.

The layer expands a question into retrieval concepts, fuses KIP hybrid-search
results, reranks them with metadata/freshness/authority, and returns a typed
answerability contract. It retrieves; it never writes the final answer.
"""

from __future__ import annotations

import re
from typing import Any

VERSION = "semantic-research-retrieval-v2.0.0"

_EXPANSIONS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (
        re.compile(
            r"\b(hyperscaler|ai (?:capex|spending|infrastructure)|data[ -]?cent(?:er|re))",
            re.I,
        ),
        (
            "hyperscaler capex",
            "AI infrastructure spending",
            "data center investment",
            "semiconductor demand",
            "power demand",
            "AI capital expenditure",
        ),
    ),
    (
        re.compile(
            r"\b(rotation|sector leadership|industries lead|market leaders)\b", re.I
        ),
        (
            "market rotation",
            "sector leadership",
            "beneficiary sectors",
            "equity leadership",
        ),
    ),
    (
        re.compile(r"\b(policy|regulation|government|tariff|subsid)", re.I),
        (
            "policy shifts",
            "regulatory change",
            "government incentives",
            "capital allocation",
        ),
    ),
    (
        re.compile(r"\b(power|utilit|electric|grid|energy demand)\b", re.I),
        (
            "power infrastructure",
            "utilities",
            "electrical equipment",
            "grid investment",
        ),
    ),
)

_SOURCE_AUTHORITY = {
    "agi_research": 1.0,
    "agi_note": 0.95,
    "company_filing": 0.9,
    "filing": 0.9,
    "broker_research": 0.75,
    "news": 0.6,
}


def _dump(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return {}


def expand_query(question: str, *, max_expansions: int = 8) -> list[str]:
    """Deterministic finance-aware expansion; never shown as user-facing prose."""
    expanded = [str(question or "").strip()]
    for pattern, concepts in _EXPANSIONS:
        if pattern.search(question or ""):
            expanded.extend(concepts)
    return list(dict.fromkeys(item for item in expanded if item))[
        : max(1, max_expansions)
    ]


def _source_priority(question: str) -> list[str]:
    q = (question or "").lower()
    if any(
        phrase in q
        for phrase in (
            "what did agi",
            "agi wrote",
            "agi's view",
            "agi view",
            "house view",
        )
    ):
        return [
            "AGI_PROPRIETARY_RESEARCH",
            "RESEARCH_MEMORY",
            "CURRENT_STRUCTURED_DATA",
            "PRIMARY_EVIDENCE",
            "EXTERNAL_RESEARCH",
        ]
    if any(word in q for word in ("forecast", "outlook", "next 5", "5-day", "5 day")):
        return [
            "CURRENT_STRUCTURED_DATA",
            "FORECAST",
            "EMPIRICAL_VALIDATION",
            "AGI_PROPRIETARY_RESEARCH",
            "RESEARCH_MEMORY",
        ]
    return [
        "CURRENT_STRUCTURED_DATA",
        "AGI_PROPRIETARY_RESEARCH",
        "RESEARCH_MEMORY",
        "PRIMARY_EVIDENCE",
        "EXTERNAL_RESEARCH",
    ]


def _metadata_score(
    hit: dict[str, Any], *, ticker: str | None, themes: list[str]
) -> float:
    score = 0.0
    if ticker and ticker.upper() in {
        str(item).upper() for item in hit.get("tickers") or []
    }:
        score += 0.65
    hit_themes = " ".join(str(item).lower() for item in hit.get("themes") or [])
    if any(theme.lower() in hit_themes for theme in themes):
        score += 0.35
    return min(1.0, score)


def _authority(hit: dict[str, Any]) -> float:
    kind = str(hit.get("document_type") or "").lower()
    return _SOURCE_AUTHORITY.get(kind, 0.5)


def _rerank(
    hit: dict[str, Any], *, ticker: str | None, themes: list[str]
) -> dict[str, Any]:
    semantic = float(hit.get("semantic_score") or hit.get("semantic") or 0)
    lexical = float(hit.get("keyword_score") or hit.get("keyword") or 0)
    metadata = _metadata_score(hit, ticker=ticker, themes=themes)
    recency = float(hit.get("freshness") or 0)
    authority = _authority(hit)
    score = (
        0.45 * semantic
        + 0.25 * lexical
        + 0.15 * metadata
        + 0.10 * recency
        + 0.05 * authority
    )
    return {
        **hit,
        "retrieval_score": round(score, 6),
        "score_components": {
            "semantic": round(semantic, 6),
            "lexical": round(lexical, 6),
            "metadata": round(metadata, 6),
            "recency": round(recency, 6),
            "authority": round(authority, 6),
        },
    }


def _answerability(hits: list[dict[str, Any]]) -> dict[str, Any]:
    top = float(hits[0].get("retrieval_score") or 0) if hits else 0.0
    relevant = sum(float(hit.get("retrieval_score") or 0) >= 0.28 for hit in hits)
    if top >= 0.42 and relevant >= 1:
        state, may_answer = "SUFFICIENT", True
    elif top >= 0.25:
        state, may_answer = "PARTIAL", True
    else:
        state, may_answer = "INSUFFICIENT", False
    return {
        "status": state,
        "may_answer": may_answer,
        "top_score": round(top, 6),
        "relevant_evidence_count": relevant,
        "required_response_behavior": {
            "SUFFICIENT": "answer_with_provenance",
            "PARTIAL": "answer_with_explicit_limitation",
            "INSUFFICIENT": "state_agi_has_insufficient_relevant_evidence",
        }[state],
    }


def _multi_hop(
    question: str,
    hits: list[dict[str, Any]],
    current: dict[str, Any],
    sector_intelligence: dict[str, Any],
) -> dict[str, Any]:
    q = (question or "").lower()
    thematic = any(
        term in q for term in ("sector", "industr", "benefit", "leadership", "rotation")
    )
    current_requested = any(
        term in q for term in ("current", "now", "confirmation", "agi see")
    )
    required = thematic and current_requested
    themes = list(
        dict.fromkeys(theme for hit in hits for theme in (hit.get("themes") or []))
    )[:8]
    return {
        "required": required,
        "stage_1": {
            "source": "AGI_RESEARCH",
            "retrieved_documents": [hit.get("document_id") for hit in hits[:5]],
            "themes": themes,
        },
        "stage_2": {
            "source": "CURRENT_INTELLIGENCE",
            "required": required,
            "available": bool(
                (current and current.get("matched")) or sector_intelligence
            ),
            "research_intelligence": current if required else {},
            "sector_intelligence": sector_intelligence if required else {},
        },
        "synthesis_rule": "separate_historical_house_view_from_current_confirmation",
    }


def package_for_ask_agi(
    question: str,
    *,
    kip: Any | None,
    ticker: str | None = None,
    themes: list[str] | None = None,
    current_intelligence: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    if kip is None or not str(question or "").strip():
        return {
            "enabled": False,
            "version": VERSION,
            "answerability": {"status": "INSUFFICIENT", "may_answer": False},
        }

    query_variants = expand_query(question)
    theme_filters = [str(item) for item in (themes or []) if item]
    fused: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for variant in query_variants:
        try:
            response = _dump(
                kip.search(
                    variant, mode="hybrid", limit=max(20, limit * 3), ticker=ticker
                )
            )
            for raw in response.get("hits") or []:
                hit = _dump(raw)
                doc_id = str(hit.get("document_id") or "")
                if not doc_id:
                    continue
                ranked = _rerank(hit, ticker=ticker, themes=theme_filters)
                ranked["matched_query"] = variant
                previous = fused.get(doc_id)
                if (
                    previous is None
                    or ranked["retrieval_score"] > previous["retrieval_score"]
                ):
                    fused[doc_id] = ranked
        except Exception as exc:
            failures.append(str(exc)[:160])

    hits = sorted(
        fused.values(), key=lambda item: item["retrieval_score"], reverse=True
    )[:limit]
    for rank, hit in enumerate(hits, start=1):
        hit["rank"] = rank
    answerability = _answerability(hits)
    current = current_intelligence or {}
    sector = sector_intelligence or {}
    return {
        "enabled": True,
        "version": VERSION,
        "query": question,
        "entity": ticker,
        "retrieval_mode": "hybrid_semantic_lexical_metadata_rerank",
        "query_expansion": {
            "applied": len(query_variants) > 1,
            "variant_count": len(query_variants),
        },
        "source_hierarchy": _source_priority(question),
        "AGI_HOUSE_VIEW": {"documents": hits, "evidence_count": len(hits)},
        "CURRENT_EVIDENCE": (
            current.get("sections", {}).get("CURRENT_EVIDENCE", {}) if current else {}
        ),
        "FORECAST": current.get("sections", {}).get("FORECAST", {}) if current else {},
        "CONTRADICTIONS": [
            hit
            for hit in hits
            if str(hit.get("stance") or "").lower() in {"bear", "contradiction"}
        ],
        "SOURCES": [
            {
                "document_id": hit.get("document_id"),
                "title": hit.get("title"),
                "document_type": hit.get("document_type"),
                "score": hit.get("retrieval_score"),
                "snippet": hit.get("snippet"),
            }
            for hit in hits
        ],
        "answerability": answerability,
        "multi_hop": _multi_hop(question, hits, current, sector),
        "data_quality": {"retrieval_failures": failures, "partial": bool(failures)},
        "answer_policy": "retrieval_only_separate_house_view_current_evidence_and_forecast",
        "guidance": {
            "do_not_reveal_query_expansions": True,
            "do_not_fill_retrieval_gaps": True,
            "cite_document_title_and_id": True,
            "forecasts_are_not_observed_facts": True,
        },
    }
