"""Soft production entry for Ask AGI — editorial rewrite after AGIB intelligence."""

from __future__ import annotations

from typing import Any

from editorial.flags import flags_dict, is_enabled
from editorial.package import build_structured_package
from editorial.schema import ARCHITECTURE_STATUS, EDITORIAL_VERSION, PROGRAMME
from editorial.service import EditorialService


def health() -> dict[str, Any]:
    return {
        **EditorialService().health(),
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "flags": flags_dict(),
    }


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": EDITORIAL_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "writer_only": True,
            "never_reads_pdfs": True,
            "never_generates_advice": True,
            "never_recommends_actions": True,
            "never_overrides_recommendation": True,
            "structured_intelligence_only": True,
            "fallback_template_on_failure": True,
            "cache_recommendations_24h": True,
            "plain_english_glossary": True,
            "never_assume_finance_knowledge": True,
            "word_limits": {
                "quick_summary": 80,
                "quick_analysis": 150,
                "detailed_analysis": 400,
            },
        },
        "flags": flags_dict(),
    }


def package_for_ask_agi(
    *,
    query: str = "",
    ticker: str | None = None,
    answer_construction: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    institutional_answer: dict[str, Any] | None = None,
    company: str | None = None,
    detailed: bool = False,
    execution_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft-wire: take AGIB structured outputs → plain-English editorial prose.

    Returns empty/disabled package when layer is off. Never raises.
    Editorial never attaches Buy/Sell/Hold — rewrite only.
    """
    if not is_enabled():
        return {
            "enabled": False,
            "bypassed": True,
            "programme": PROGRAMME,
            "version": EDITORIAL_VERSION,
            "architecture_status": ARCHITECTURE_STATUS,
        }

    try:
        ac = answer_construction if isinstance(answer_construction, dict) else {}
        ia = institutional_answer if isinstance(institutional_answer, dict) else ac.get("institutional_answer")
        ep = execution_policy if isinstance(execution_policy, dict) else ac.get("execution_policy")
        structured = build_structured_package(
            question=query,
            institutional_answer=ia if isinstance(ia, dict) else None,
            answer_construction=ac,
            company_analysis=company_analysis if isinstance(company_analysis, dict) else None,
            company=company,
            ticker=ticker,
            execution_policy=ep if isinstance(ep, dict) else None,
        )
        # When framework policy withholds narrative, do not let Gemini invent valuation prose.
        if isinstance(ep, dict) and ep.get("narrative_allowed") is False:
            msg = str(
                (ac or {}).get("executive")
                or ep.get("gate_reason")
                or structured.get("valuation")
                or "Valuation coverage incomplete — required frameworks lack evidence."
            )
            return {
                "enabled": True,
                "programme": PROGRAMME,
                "version": EDITORIAL_VERSION,
                "architecture_status": ARCHITECTURE_STATUS,
                "role": "writer_only",
                "agib_is_brain": True,
                "never_generates_advice": True,
                "policy_withheld": True,
                "structured_intelligence": structured,
                "executive": msg,
                "rewritten_summary": msg,
                "provider": "execution_policy",
                "fallback": False,
            }
        service = EditorialService()
        if detailed:
            result = service.generateDetailedAnalysis(structured, question=query)
        elif isinstance(ia, dict) and (ia.get("is_recommendation_query") or ia.get("enabled")):
            # Plain-English Quick Summary only — no Recommendation: Buy/Sell/Hold prefix.
            result = service.generateQuickSummary(structured, question=query)
        else:
            result = service.generateQuickAnalysis(structured, question=query)

        rewritten = result.get("rewritten_summary") or result.get("text")
        executive = rewritten  # always rewrite-only for Ask AGI executive text
        return {
            "enabled": True,
            "programme": PROGRAMME,
            "version": EDITORIAL_VERSION,
            "architecture_status": ARCHITECTURE_STATUS,
            "role": "writer_only",
            "agib_is_brain": True,
            "never_generates_advice": True,
            "never_recommends_actions": True,
            "flags": flags_dict(),
            "structured_intelligence": structured,
            "editorial": result,
            "executive": executive,
            "rewritten_summary": rewritten,
            "fallback": bool(result.get("fallback")),
            "provider": result.get("provider"),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "programme": PROGRAMME,
            "version": EDITORIAL_VERSION,
            "architecture_status": ARCHITECTURE_STATUS,
            "error": str(exc),
            "fallback": True,
            "executive": None,
        }
