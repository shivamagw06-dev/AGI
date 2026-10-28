"""Compile existing Ask AGI retrieval into a privacy-safe skill payload.

This layer performs no I/O. It cannot read files, environment variables, secrets,
or network resources. It only minimizes and labels evidence already retrieved by
approved AGI adapters.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from finance_research_skill.evidence_tagger import tag_documents

VERSION = "agi-finance-research-v1.0.0"

_DENIED_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credentials",
    "password",
    "prompt",
    "query",
    "raw",
    "raw_text",
    "secret",
    "service_role_key",
    "token",
}


def _safe(value: Any, *, depth: int = 0) -> Any:
    """Minimize evidence and remove fields that can carry secrets or raw prompts."""
    if depth > 7:
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:1200]
    if isinstance(value, (list, tuple)):
        return [_safe(item, depth=depth + 1) for item in value[:50]]
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in list(value.items())[:100]:
            label = str(key)
            normalized = label.lower().replace("-", "_")
            if normalized in _DENIED_KEYS or normalized.endswith("_token"):
                continue
            clean[label] = _safe(item, depth=depth + 1)
        return clean
    return str(value)[:300]


def _route(
    *, entity: str | None, semantic: dict[str, Any], research: dict[str, Any]
) -> str:
    if entity:
        return "COMPANY_RESEARCH"
    intent = str(research.get("intent") or "")
    if intent == "pipeline_health":
        return "PIPELINE_HEALTH"
    hierarchy = semantic.get("source_hierarchy") or []
    if hierarchy and hierarchy[0] == "AGI_PROPRIETARY_RESEARCH":
        return "HOUSE_RESEARCH"
    return "THEMATIC_RESEARCH"


def _answerability(
    *, route: str, semantic: dict[str, Any], research: dict[str, Any]
) -> str:
    semantic_status = str((semantic.get("answerability") or {}).get("status") or "")
    quality = ((research.get("sections") or {}).get("DATA_QUALITY") or {})
    research_matched = bool(research.get("matched"))
    if route in {"HOUSE_RESEARCH", "THEMATIC_RESEARCH"}:
        return semantic_status if semantic_status in {"SUFFICIENT", "PARTIAL"} else "INSUFFICIENT"
    if not research_matched:
        return "INSUFFICIENT"
    if quality.get("retrieval_failures") or not quality.get("evidence_complete", True):
        return "PARTIAL"
    return "SUFFICIENT"


def compile_evidence_contract(
    *,
    entity: str | None,
    research_intelligence: dict[str, Any] | None,
    semantic_research: dict[str, Any] | None,
    sector_intelligence: dict[str, Any] | None = None,
    request_id: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return the only payload the AGI Finance Research skill may consume."""
    research = research_intelligence if isinstance(research_intelligence, dict) else {}
    semantic = semantic_research if isinstance(semantic_research, dict) else {}
    sector = sector_intelligence if isinstance(sector_intelligence, dict) else {}
    route = _route(entity=entity, semantic=semantic, research=research)
    sections = research.get("sections") if isinstance(research.get("sections"), dict) else {}
    quality = sections.get("DATA_QUALITY") if isinstance(sections.get("DATA_QUALITY"), dict) else {}
    answerability = _answerability(route=route, semantic=semantic, research=research)
    house = semantic.get("AGI_HOUSE_VIEW") if isinstance(semantic.get("AGI_HOUSE_VIEW"), dict) else {}
    sources = semantic.get("SOURCES") if isinstance(semantic.get("SOURCES"), list) else []
    documents = house.get("documents") if isinstance(house.get("documents"), list) else []
    evidence_tags = tag_documents(documents, entity=entity)
    missing = list(quality.get("missing_components") or [])
    if answerability == "INSUFFICIENT" and not missing:
        missing.append("relevant_evidence")

    return {
        "skill": {"name": "agi-finance-research", "version": VERSION},
        "request_id": str(request_id or "")[:120] or None,
        "route": route,
        "company_required": route == "COMPANY_RESEARCH",
        "entity": {"symbol": str(entity).upper()} if entity else None,
        "as_of": as_of or datetime.now(timezone.utc).isoformat(),
        "answerability": answerability,
        "evidence_complete": answerability == "SUFFICIENT" and not missing,
        "missing_components": missing,
        "current_evidence": _safe(sections.get("CURRENT_EVIDENCE") or {}),
        "house_research": _safe(house.get("documents") or []),
        "evidence_tags": _safe(evidence_tags),
        "forecasts": _safe(sections.get("FORECAST") or {}),
        "historical_outcomes": _safe(sections.get("HISTORICAL_OUTCOME") or {}),
        "validation": _safe(sections.get("EMPIRICAL_VALIDATION") or {}),
        "contradictions": _safe(semantic.get("CONTRADICTIONS") or []),
        "sector_context": _safe(sector),
        "provenance": _safe(sources),
        "data_quality": _safe(quality),
        "privacy": {
            "filesystem_access": False,
            "credential_access": False,
            "external_uploads": False,
            "raw_prompt_included": False,
            "typed_evidence_only": True,
        },
        "answer_policy": "facts_house_view_forecasts_and_interpretation_remain_separate",
    }
