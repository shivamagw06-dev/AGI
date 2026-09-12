"""Production facade for Industry Intelligence Engine — unwired to Ask until Acceptance 100%."""

from __future__ import annotations

from typing import Any, Optional

from industry_intelligence.dna_catalog import INDUSTRY_DNA
from industry_intelligence.registry import all_industry_keys, registry_snapshot, resolve_industry
from industry_intelligence.schema import ASK_WIRED, ASK_WIRED_VIA, II_VERSION, PROGRAMME, SPEC
from industry_intelligence import engines
from industry_intelligence.orchestrator import analyse as _analyse


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "status": "ok",
        "programme": PROGRAMME,
        "version": II_VERSION,
        "spec": SPEC,
        "ask_wired": ASK_WIRED,
        "ask_wired_via": ASK_WIRED_VIA if ASK_WIRED else None,
        "ask_wired_policy": "kul_provider_only_after_acceptance_100",
        "uses_llm": False,
        "fabricated": False,
        "depends_on": "AGI Core v1.0 (extend, do not modify)",
        "industry_count": len(INDUSTRY_DNA),
        "industries": all_industry_keys(),
        "modules": [
            "registry",
            "dna",
            "kpis",
            "economics",
            "cycle",
            "regulation",
            "valuation",
            "competition",
            "risks",
            "graph",
            "cross_industry",
        ],
        "api_prefix": "/v1/industry-intelligence",
    }


def dashboard() -> dict[str, Any]:
    return {
        "version": II_VERSION,
        "ask_wired": ASK_WIRED,
        "industry_count": len(INDUSTRY_DNA),
        "registry": registry_snapshot(),
        "fabricated": False,
    }


def analyse(question: str, *, industry: Optional[str] = None) -> dict[str, Any]:
    key = industry or resolve_industry(question)
    return _analyse(question, industry=key)


def industry(industry_key: str) -> dict[str, Any]:
    key = resolve_industry(industry_key) or industry_key
    dna = engines.dna_view(key)
    if not dna.get("found"):
        return {"found": False, "key": industry_key, "fabricated": False}
    return {
        "found": True,
        "key": key,
        "dna": dna,
        "economics": engines.economics(key),
        "kpis": engines.kpis(key),
        "valuation": engines.valuation(key),
        "regulation": engines.regulation(key),
        "competition": engines.competition(key),
        "cycle": engines.cycle(key),
        "risks": engines.risks(key),
        "graph": engines.graph(key),
        "fabricated": False,
    }


def explain_kpi(industry_key: str, kpi_key: str) -> dict[str, Any]:
    key = resolve_industry(industry_key) or industry_key
    return engines.kpis(key, kpi_key)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Diagnostics preview — production Ask uses KUL provider only (no bypass)."""
    if not ASK_WIRED:
        return {
            "found": False,
            "ask_wired": False,
            "reason": "Industry Intelligence not wired into Ask until Acceptance = 100%",
            "fabricated": False,
        }
    out = analyse(question)
    return {
        "found": bool(out.get("ok") and out.get("summary")),
        "ask_wired": True,
        "ask_wired_via": ASK_WIRED_VIA,
        "enabled": True,
        **out,
    }
