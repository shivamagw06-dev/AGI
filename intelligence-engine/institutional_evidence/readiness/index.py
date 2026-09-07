"""Research Readiness Index — Research Ready or Research Blocked."""

from __future__ import annotations

from typing import Any, Dict

from ..schema import READINESS_WEIGHTS, RESEARCH_READY_THRESHOLD


def compute_research_readiness(pack: Dict[str, Any]) -> Dict[str, Any]:
    components: Dict[str, float] = {}
    financials = pack.get("financials") or {}
    evidence = pack.get("evidence") or {}
    reg = evidence.get("registry") or {}
    items = reg.get("items") or []
    memory = pack.get("company_memory") or {}
    kg = pack.get("knowledge_graph") or {}
    decision = pack.get("decision") or {}
    valuation = pack.get("valuation") or {}

    # primary filings
    primary = sum(1 for i in items if i.get("research_ready") or i.get("authority_score", 0) >= 0.85)
    components["primary_filings"] = min(1.0, primary / 2.0) * 100.0

    # financial statements
    periods = financials.get("periods") or []
    if financials.get("published") and len(periods) >= 4:
        components["financial_statements"] = 100.0
    elif financials.get("published") and periods:
        components["financial_statements"] = 60.0
    elif periods:
        components["financial_statements"] = 30.0
    else:
        components["financial_statements"] = 0.0

    # segment coverage
    seg = financials.get("segment_revenue") or []
    components["segment_coverage"] = 100.0 if seg else (40.0 if periods else 0.0)

    # valuation inputs
    components["valuation_inputs"] = 80.0 if valuation else (30.0 if periods else 0.0)

    # evidence completeness
    ec = len(items)
    components["evidence_completeness"] = min(100.0, ec * 25.0)

    # freshness
    fresh_ok = [i for i in items if i.get("freshness_ok")]
    if items:
        components["freshness"] = 100.0 * (len(fresh_ok) / len(items))
    else:
        components["freshness"] = 0.0

    # knowledge graph
    components["knowledge_graph"] = 80.0 if kg else 20.0 * float(memory.get("slot_coverage") or 0)

    # financial intelligence (proxy: ratios present)
    ratios = financials.get("ratios") or {}
    components["financial_intelligence"] = 70.0 if ratios else 0.0

    # decision consistency — no decisive rec without statements
    rec = str(
        decision.get("recommendation") or decision.get("action") or decision.get("rating") or ""
    ).upper()
    from ..schema import BLOCKED_RECOMMENDATIONS

    if not periods and rec in BLOCKED_RECOMMENDATIONS:
        components["decision_consistency"] = 0.0
    elif periods and rec:
        components["decision_consistency"] = 80.0
    else:
        components["decision_consistency"] = 50.0 if not rec else 60.0

    weighted = 0.0
    detail = {}
    for key, weight in READINESS_WEIGHTS.items():
        score = float(components.get(key, 0.0))
        weighted += (score / 100.0) * weight
        detail[key] = {"score": round(score, 2), "weight": weight}

    research_ready = weighted >= RESEARCH_READY_THRESHOLD
    return {
        "ok": True,
        "score": round(weighted, 2),
        "readiness_score": round(weighted, 2),
        "threshold": RESEARCH_READY_THRESHOLD,
        "research_ready": research_ready,
        "status": "Research Ready" if research_ready else "Research Blocked",
        "components": detail,
        "publishing_allowed": research_ready,
    }
