"""Decision Eligibility — engine must earn permission before recommending."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..schema import (
    ALLOWED_WHEN_BLOCKED,
    BLOCKED_RECOMMENDATIONS,
    RESEARCH_READY_THRESHOLD,
)


def evaluate_decision_eligibility(
    ticker: str,
    *,
    pack: Optional[Dict[str, Any]] = None,
    quality: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Future flow: Decision Eligibility → Decision Engine.

    The engine first earns permission to recommend.
    """
    from ..research_pack.builder import build_institutional_research_pack
    from ..quality.engine import evaluate_evidence_quality

    t = str(ticker or "").upper().strip()
    p = pack if isinstance(pack, dict) else build_institutional_research_pack(t)
    fin = p.get("financials") or {}
    q = quality or evaluate_evidence_quality(
        canonical_financials=fin,
        registry_items=((p.get("evidence") or {}).get("registry") or {}).get("items") or [],
    )

    # Knowledge confidence (KIL) — Decision Engine never checks providers
    kc = None
    try:
        from ..integration.confidence.score import compute_knowledge_confidence
        from ..integration.layer import get_integrated_company

        integ = get_integrated_company(t)
        if integ and integ.get("knowledge_confidence"):
            kc = integ["knowledge_confidence"]
        else:
            kc = compute_knowledge_confidence(t, pack=p)
    except Exception:
        kc = None

    checks = {
        "knowledge_ready": bool(
            (kc or {}).get("above_threshold")
            or (fin.get("published") and not fin.get("zero_periods"))
        ),
        "evidence_complete": bool(p.get("claim_safe")),
        "financial_statements_published": bool(fin.get("published") and not fin.get("zero_periods")),
        "research_ready": bool(p.get("research_ready")),
        "claim_safe": bool(p.get("claim_safe")),
        "quality_publishable": bool(q.get("publish_allowed")),
        "knowledge_confidence_ok": bool((kc or {}).get("above_threshold")) if kc else None,
        "sector_validation": bool(p.get("sector")),
    }
    # Soft-consume IDRE if present
    idre = None
    try:
        from decision_readiness.production import get_readiness  # type: ignore

        idre = get_readiness(t)
        if isinstance(idre, dict):
            status = str(idre.get("status") or idre.get("band") or "").upper()
            checks["idre_ready"] = status in {"READY", "CONDITIONAL", "CONDITIONS"}
    except Exception:
        checks["idre_ready"] = None

    required = (
        "knowledge_ready",
        "research_ready",
        "claim_safe",
        "financial_statements_published",
        "evidence_complete",
    )
    eligible = all(bool(checks.get(k)) for k in required)
    if checks.get("knowledge_confidence_ok") is False:
        eligible = False
    # idre_ready if present must not hard-block unless NOT READY
    if checks.get("idre_ready") is False:
        eligible = False

    score = (p.get("research_readiness") or {}).get("score")
    return {
        "ok": True,
        "ticker": t,
        "eligible": eligible,
        "permission": "RECOMMENDATION_PERMITTED" if eligible else "RECOMMENDATION_DENIED",
        "allowed_actions_if_denied": list(ALLOWED_WHEN_BLOCKED),
        "blocked_actions": list(BLOCKED_RECOMMENDATIONS),
        "checks": checks,
        "research_readiness_score": score,
        "research_ready_threshold": RESEARCH_READY_THRESHOLD,
        "evidence_quality_score": q.get("evidence_quality_score"),
        "knowledge_confidence": (kc or {}).get("knowledge_confidence") if kc else None,
        "next": "decision_engine" if eligible else "NO RECOMMENDATION / MONITOR",
        "rule": "Decision Engine never checks providers — only InstitutionalResearchPack + KIL knowledge",
        "idre_soft": idre if isinstance(idre, dict) else None,
    }
