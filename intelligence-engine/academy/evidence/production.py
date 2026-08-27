"""Evidence Intelligence Layer — production facade."""

from __future__ import annotations

from typing import Any

from academy.evidence.attach import enrich_case, support_statement
from academy.evidence.confidence import decompose_confidence
from academy.evidence.schema import EIL_VERSION


def is_enabled() -> bool:
    try:
        from app.core.config import get_settings

        s = get_settings()
        return bool(getattr(s, "academy", True)) and bool(
            getattr(s, "evidence_intelligence_layer", True)
        )
    except Exception:
        return True


def dashboard() -> dict[str, Any]:
    case = enrich_case("acs_live_11_jul2026")
    peer_slice: dict[str, Any] = {}
    try:
        from peer_intelligence.production import soft_slice_for_eil

        peer_slice = soft_slice_for_eil()
    except Exception as exc:
        peer_slice = {"peer_intelligence": {"enabled": False, "soft_error": str(exc)}}
    filing_slice: dict[str, Any] = {}
    try:
        from filing_intelligence.production import soft_slice_for_eil as fil_soft_eil

        filing_slice = fil_soft_eil()
    except Exception as exc:
        filing_slice = {"filing_intelligence": {"enabled": False, "soft_error": str(exc)}}
    return {
        "programme": "AGIB_EVIDENCE_INTELLIGENCE_LAYER",
        "eil_version": EIL_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "objective": "Support every major claim with sources, history/peer gaps, explainable confidence",
        "primary_weakness_addressed": "ACS/IRS evidence quality — stop priors-as-facts and unnamed Street",
        "live_case": {
            "case_id": case.get("case_id"),
            "title": case.get("title"),
            "summary": case.get("summary"),
        },
        "rules": case.get("institutional_rules"),
        "no_redesign": [
            "engine",
            "ui",
            "provider",
            "certification",
            "regression",
            "academy_books",
            "analysts",
        ],
        **peer_slice,
        **filing_slice,
    }


def case_pack(case_id: str = "acs_live_11_jul2026") -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False}
    return {"enabled": True, **enrich_case(case_id)}


def explain_confidence(
    *,
    evidence: float,
    historical: float,
    peer: float,
    macro: float = 70.0,
) -> dict[str, Any]:
    return decompose_confidence(
        evidence=evidence, historical=historical, peer=peer, macro=macro
    )


def support(statement: str, *, analyst: str | None = None) -> dict[str, Any]:
    return support_statement(statement, analyst=analyst)


def quality_gates() -> dict[str, Any]:
    case = enrich_case("acs_live_11_jul2026")
    claims = case.get("claims") or []
    priors_as_facts = [
        c for c in claims
        if c.get("epistemic_label") == "prior" and c.get("is_evidence")
    ]
    street = [c for c in claims if c.get("epistemic_label") == "street"]
    street_sourced = all(c.get("attached_sources") for c in street)
    facts = [c for c in claims if c.get("epistemic_label") == "fact"]
    facts_sourced = all(c.get("attached_sources") for c in facts)
    triggers = case.get("decision_triggers") or []

    checks = {
        "enabled": is_enabled(),
        "live_case_loaded": case.get("case_id") == "acs_live_11_jul2026",
        "no_priors_marked_as_evidence": len(priors_as_facts) == 0,
        "facts_have_sources": facts_sourced and len(facts) >= 3,
        "street_claims_name_sources": street_sourced and len(street) >= 1,
        "confidence_has_breakdown": all(
            "breakdown" in (c.get("confidence_breakdown") or {}) for c in facts
        ),
        "decision_triggers_present": len(triggers) >= 3,
        "peer_gaps_visible": (case.get("summary") or {}).get("open_gaps", 0) >= 1,
        "macro_transmission_extended": len(case.get("transmission_macro") or []) >= 7,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "eil_version": EIL_VERSION,
        "summary": case.get("summary"),
    }


def soft_slice_for_irs() -> dict[str, Any]:
    """Minimal block for IRS dashboard / gate commentary."""
    if not is_enabled():
        return {}
    q = quality_gates()
    dash = dashboard()
    return {
        "evidence_intelligence": {
            "enabled": True,
            "version": EIL_VERSION,
            "quality_gates_passed": q.get("passed"),
            "live_case": dash.get("live_case"),
            "recommendation": (
                "Use EIL attachments for every major ACS/IRS claim; "
                "do not add frameworks until peer/history gaps close."
            ),
        }
    }
