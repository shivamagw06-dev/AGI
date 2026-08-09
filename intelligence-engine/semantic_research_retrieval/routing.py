"""Deterministic Ask AGI routing before company identity enforcement."""

from __future__ import annotations

import re
from typing import Any

HOUSE_RESEARCH = "HOUSE_RESEARCH"
THEMATIC_RESEARCH = "THEMATIC_RESEARCH"
COMPANY_RESEARCH = "COMPANY_RESEARCH"

_LISTED_AGI_COMPANY_RE = re.compile(r"\bagi\s+(?:greenpac|infra)\b", re.I)
_HOUSE_RESEARCH_RE = re.compile(
    r"\b(?:global investment monitor|agi(?:['’]s)?\s+(?:house\s+view|research|view|views|"
    r"thinks?|expects?|says?|wrote)|(?:what|how)\s+(?:does|did|is|was)\s+agi\s+"
    r"(?:think|view|say|expect|write)|according\s+to\s+agi)\b",
    re.I,
)
_THEMATIC_RESEARCH_RE = re.compile(
    r"\b(?:ai\s+(?:spending|investment|capex|infrastructure)|hyperscaler|"
    r"data[ -]?cent(?:er|re)|sector\s+rotation|sector\s+leadership|policy\s+shifts?|"
    r"market\s+rotation|beneficiary\s+sectors?|industr(?:y|ies|ial)|power\s+(?:names?|companies|demand)|"
    r"capital\s+spending)\b",
    re.I,
)


def classify_research_route(question: str) -> str:
    """Return the routing class needed by the company identity gate."""
    q = str(question or "").strip()
    if _LISTED_AGI_COMPANY_RE.search(q):
        return COMPANY_RESEARCH
    if _HOUSE_RESEARCH_RE.search(q):
        return HOUSE_RESEARCH
    if _THEMATIC_RESEARCH_RE.search(q):
        return THEMATIC_RESEARCH
    return COMPANY_RESEARCH


def company_required(question: str) -> bool:
    return classify_research_route(question) == COMPANY_RESEARCH


def initial_research_trace(question: str) -> dict[str, Any]:
    route = classify_research_route(question)
    return {
        "query": str(question or "").strip(),
        "route": route,
        "company_required": route == COMPANY_RESEARCH,
        "semantic_retrieval": "PENDING",
        "matched_documents": [],
        "global_investment_monitor": "NOT_CHECKED",
        "answerability": "PENDING",
        "answer_synthesis": "PENDING",
        "failure_stage": None,
    }


def record_semantic_retrieval(
    trace: dict[str, Any], package: dict[str, Any] | None
) -> dict[str, Any]:
    out = dict(trace or {})
    pack = package if isinstance(package, dict) else {}
    documents = ((pack.get("AGI_HOUSE_VIEW") or {}).get("documents") or [])
    matches = [
        {
            "document_id": item.get("document_id"),
            "title": item.get("title"),
            "score": item.get("retrieval_score"),
        }
        for item in documents
        if isinstance(item, dict)
    ]
    answerability = str((pack.get("answerability") or {}).get("status") or "INSUFFICIENT")
    monitor_match = any(
        "global investment monitor" in str(item.get("title") or "").lower()
        for item in matches
    )
    out.update(
        {
            "semantic_retrieval": "EXECUTED" if pack.get("enabled") else "NOT_EXECUTED",
            "matched_documents": matches[:8],
            "global_investment_monitor": "MATCH" if monitor_match else "NO_MATCH",
            "answerability": answerability,
        }
    )
    if out["semantic_retrieval"] != "EXECUTED":
        out["failure_stage"] = "ROUTING"
    elif not matches:
        out["failure_stage"] = "RETRIEVAL"
    elif answerability == "INSUFFICIENT":
        out["failure_stage"] = "EVIDENCE_INSUFFICIENCY"
    else:
        out["failure_stage"] = None
    return out


def record_answer_synthesis(
    trace: dict[str, Any], *, completed: bool
) -> dict[str, Any]:
    out = dict(trace or {})
    out["answer_synthesis"] = "EXECUTED" if completed else "FAILED"
    if not completed:
        out["failure_stage"] = "SYNTHESIS"
    return out


__all__ = [
    "COMPANY_RESEARCH",
    "HOUSE_RESEARCH",
    "THEMATIC_RESEARCH",
    "classify_research_route",
    "company_required",
    "initial_research_trace",
    "record_answer_synthesis",
    "record_semantic_retrieval",
]
