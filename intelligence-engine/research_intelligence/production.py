"""Production facade for Phase 3.4 Research Intelligence.

Ask soft-slice blocked until Acceptance = 100% and ASK_WIRED flips.
"""

from __future__ import annotations

from typing import Any, Optional

from research_intelligence.corpus import list_entities
from research_intelligence.orchestrator import analyse as _analyse
from research_intelligence.schema import (
    ASK_WIRED,
    ASK_WIRED_VIA,
    KNOWLEDGE_AUTHORITY,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    RI_VERSION,
    SPEC,
)


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "module": "research_intelligence",
        "programme": PROGRAMME,
        "phase": "3.4",
        "version": RI_VERSION,
        "spec": SPEC,
        "ask_wired": ASK_WIRED,
        "ask_wired_via": ASK_WIRED_VIA if ASK_WIRED else None,
        "ask_wired_policy": "kul_provider_only_after_acceptance_100",
        "uses_llm": False,
        "fabricated": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "knowledge_authority": KNOWLEDGE_AUTHORITY,
        "depends_on": [
            "AGI Core v1.1 (extend, do not modify)",
            "Investment Intelligence 3.2",
            "Portfolio Intelligence 3.3",
        ],
        "entity_count": len(list_entities()),
        "entities": list_entities(),
        "modules": [
            "research_object",
            "annual_report",
            "transcript",
            "management",
            "guidance",
            "estimates",
            "events",
            "memory",
            "cross_document",
            "timeline",
            "quality",
            "knowledge_evolution",
            "deep_research",
        ],
        "api_prefix": "/v1/research-intelligence",
    }


def dashboard() -> dict[str, Any]:
    return {
        "ok": True,
        "version": RI_VERSION,
        "ask_wired": ASK_WIRED,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "knowledge_authority": KNOWLEDGE_AUTHORITY,
        "entities": list_entities(),
        "modules": health()["modules"],
        "fabricated": False,
    }


def entities() -> dict[str, Any]:
    return {"ok": True, "entities": list_entities(), "version": RI_VERSION}


def analyse(question: str, *, entity: Optional[str] = None) -> dict[str, Any]:
    return _analyse(question, entity=entity)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Diagnostics preview only — Ask production path uses KUL (no bypass)."""
    if not ASK_WIRED:
        return {
            "found": False,
            "ask_wired": False,
            "reason": "Research Intelligence not wired into Ask until Acceptance = 100%",
            "recommendation_policy": RECOMMENDATION_POLICY,
            "fabricated": False,
        }
    out = analyse(question)
    return {
        "found": bool(out.get("ok") and out.get("summary")),
        "ask_wired": True,
        "ask_wired_via": ASK_WIRED_VIA,
        "enabled": True,
        "recommendation_policy": RECOMMENDATION_POLICY,
        **out,
    }


__all__ = ["analyse", "dashboard", "entities", "health", "soft_slice_for_ask_agi"]
