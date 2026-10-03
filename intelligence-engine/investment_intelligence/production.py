"""Production facade for Investment Intelligence — unwired to Ask until Acceptance 100%."""

from __future__ import annotations

from typing import Any, Optional

from investment_intelligence.orchestrator import analyse as _analyse
from investment_intelligence.profiles import list_profiles, resolve_entity
from investment_intelligence.schema import (
    ASK_WIRED,
    ASK_WIRED_VIA,
    IIE_VERSION,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
)


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "programme": PROGRAMME,
        "version": IIE_VERSION,
        "spec": SPEC,
        "ask_wired": ASK_WIRED,
        "ask_wired_via": ASK_WIRED_VIA if ASK_WIRED else None,
        "ask_wired_policy": "kul_provider_only_after_acceptance_100",
        "uses_llm": False,
        "fabricated": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "depends_on": ["AGI Core v1.1 (extend)", "Business Intelligence", "Industry Intelligence"],
        "profile_count": len(list_profiles()),
        "profiles": list_profiles(),
        "modules": [
            "thesis",
            "quality",
            "catalysts",
            "risks",
            "scenarios",
            "valuation",
            "capital_allocation",
            "evidence",
            "committee",
            "graph",
        ],
        "api_prefix": "/v1/investment-intelligence",
    }


def dashboard() -> dict[str, Any]:
    h = health()
    return {
        "version": IIE_VERSION,
        "ask_wired": ASK_WIRED,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "profile_count": h["profile_count"],
        "modules": h["modules"],
        "fabricated": False,
    }


def analyse(question: str, *, entity: Optional[str] = None) -> dict[str, Any]:
    key = entity or resolve_entity(question)
    return _analyse(question, entity=key)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Diagnostics preview — production Ask uses KUL provider only (no bypass)."""
    if not ASK_WIRED:
        return {
            "found": False,
            "ask_wired": False,
            "reason": "Investment Intelligence not wired into Ask until Acceptance = 100%",
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
