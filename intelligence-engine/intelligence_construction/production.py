"""Ask AGI Intelligence Construction V2 — production soft entry."""

from __future__ import annotations

from typing import Any

from intelligence_construction.brief import build_institutional_research_brief
from intelligence_construction.flags import flags_dict, is_enabled
from intelligence_construction.schema import ARCHITECTURE_STATUS, IC_VERSION, PROGRAMME


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "version": IC_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "never_expose_providers": True,
        "flags": flags_dict(),
    }


def package_for_ask_agi(
    query: str = "",
    *,
    ticker: str | None = None,
    cid: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    company_monitor: dict[str, Any] | None = None,
    finance_academy: dict[str, Any] | None = None,
    knowledge_foundation: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    data_validation: dict[str, Any] | None = None,
    evidence_completion: dict[str, Any] | None = None,
    irp: dict[str, Any] | None = None,
    investment_office: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft entry used by UiService after CID/CA/Monitor/IRP packages are available."""
    return build_institutional_research_brief(
        query=query,
        ticker=ticker,
        cid=cid,
        company_analysis=company_analysis,
        company_monitor=company_monitor,
        finance_academy=finance_academy,
        knowledge_foundation=knowledge_foundation,
        live_evidence=live_evidence,
        data_validation=data_validation,
        evidence_completion=evidence_completion,
        irp=irp,
        investment_office=investment_office,
        sector_intelligence=sector_intelligence,
    )


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": IC_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "never_expose_providers": True,
            "consumes_canonical_models_only": True,
        },
        "flags": flags_dict(),
    }
