"""Step 10 — Recommendation readiness (gate unchanged; never auto-recommend)."""

from __future__ import annotations

from typing import Any


def evaluate_readiness(
    *,
    financial: dict[str, Any] | None = None,
    valuation: dict[str, Any] | None = None,
    sector: dict[str, Any] | None = None,
    academy_applied: dict[str, Any] | None = None,
    business_quality: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
    dvc_pkg: dict[str, Any] | None = None,
    irp_pkg: dict[str, Any] | None = None,
    forecast_learning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def pct(*vals: Any, default: int = 0) -> int:
        for v in vals:
            if isinstance(v, (int, float)):
                return max(0, min(100, int(round(float(v)))))
        return default

    financial_cov = pct((financial or {}).get("coverage_pct"), default=40 if (financial or {}).get("enabled") else 0)
    valuation_cov = pct((valuation or {}).get("coverage_pct"), default=40 if (valuation or {}).get("enabled") else 0)
    sector_cov = pct((sector or {}).get("coverage_pct"), default=50 if (sector or {}).get("sector_id") else 20)
    knowledge_cov = min(100, 40 + 5 * len((academy_applied or {}).get("applied_concepts") or []))
    knowledge_cov = pct((business_quality or {}).get("coverage_pct"), knowledge_cov, default=knowledge_cov)

    research_cov = 50
    if cid and (cid.get("evidence_timeline") or cid.get("research")):
        research_cov = 75
    if irp_pkg:
        research_cov = max(research_cov, 85)
    if leo_pkg and (leo_pkg.get("evidence_objects") or []):
        research_cov = min(100, research_cov + 10)

    prediction_cov = 40
    if forecast_learning and (forecast_learning.get("company") or forecast_learning.get("forecasts")):
        prediction_cov = 81

    evidence_conf = 55
    if dvc_pkg and dvc_pkg.get("quality"):
        q = str(dvc_pkg.get("quality")).lower()
        evidence_conf = 90 if q in {"high", "a", "good"} else 70 if q in {"medium", "b"} else 55
    if leo_pkg and (leo_pkg.get("quality_gate") or {}).get("blocked"):
        evidence_conf = min(evidence_conf, 45)

    scores = {
        "financial_intelligence": financial_cov,
        "valuation": valuation_cov,
        "sector_intelligence": sector_cov,
        "knowledge": knowledge_cov,
        "research": research_cov,
        "prediction_history": prediction_cov,
        "evidence_confidence": evidence_conf,
    }
    overall = int(round(sum(scores.values()) / len(scores)))

    # Never auto-recommend. Eligible only means coverage sufficient for institutional analysis.
    gate = "Eligible" if overall >= 70 and financial_cov >= 40 and knowledge_cov >= 50 else "Recommendation Withheld"
    reasons = []
    if financial_cov < 40:
        reasons.append("Financial coverage below institutional threshold")
    if valuation_cov < 30:
        reasons.append("Valuation coverage incomplete")
    if knowledge_cov < 50:
        reasons.append("Academy/knowledge application incomplete")
    if evidence_conf < 50:
        reasons.append("Evidence confidence insufficient or LEO gate blocked")
    if gate == "Eligible":
        reasons.append("Coverage sufficient for analysis — still not an automatic buy/sell recommendation")

    return {
        "scores": scores,
        "overall": overall,
        "gate": gate,
        "explanation": reasons,
        "not_a_recommendation_engine": True,
        "recommendation_gate_unchanged": True,
    }
