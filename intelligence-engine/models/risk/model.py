"""Risk Intelligence — multi-dimensional risk matrix."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.objects import RiskProfile

RISK_KEYS = [
    "business_risk",
    "financial_risk",
    "governance_risk",
    "operational_risk",
    "regulatory_risk",
    "macro_risk",
    "currency_risk",
    "commodity_risk",
    "interest_rate_risk",
    "technology_risk",
    "execution_risk",
    "customer_risk",
    "supplier_risk",
    "climate_risk",
    "cyber_risk",
]


class RiskModel(DomainModel):
    """Structured risk matrix with probability, severity and monitoring signals."""

    domain = "risk"
    version = "1.0.0"
    name = "Risk Intelligence"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        matrix = []
        for key in RISK_KEYS:
            block = p.get(key) if isinstance(p.get(key), dict) else {}
            probability = num(block, "probability", num(p, f"{key}_probability", 0.3))
            severity = num(block, "severity", num(p, f"{key}_severity", 0.3))
            score = clamp(probability * severity)
            matrix.append(
                {
                    "risk": key,
                    "probability": round(probability, 4),
                    "severity": round(severity, 4),
                    "score": round(score, 4),
                    "mitigation": (block or {}).get("mitigation") or f"Monitor {key.replace('_', ' ')}",
                }
            )
        matrix.sort(key=lambda r: r["score"], reverse=True)
        overall = clamp(sum(r["score"] for r in matrix[:5]) / 5.0)
        # Invert for "quality-like" score used by decision (higher = safer)
        safety = clamp(1.0 - overall)
        signals = [f"Elevated {r['risk']}" for r in matrix[:3] if r["score"] >= 0.25]
        mitigations = [r["mitigation"] for r in matrix[:5]]
        label = "high" if overall >= 0.45 else "moderate" if overall >= 0.25 else "low"
        summary = f"{sid} overall risk {label}. Top risks: {', '.join(r['risk'] for r in matrix[:3])}."
        profile = RiskProfile(
            subject_id=sid,
            overall_risk_score=round(overall, 4),
            risk_matrix=matrix,
            monitoring_signals=signals,
            mitigations=mitigations,
            version=self.version,
        )
        return AnalysisResult(
            object_type="RiskProfile",
            object_id=new_id("rsk"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(safety, 4),  # higher = safer for compare/decision
            label=label,
            confidence=0.7,
            summary=summary,
            outputs={"risk": profile.to_dict(), "safety_score": safety, "raw_risk": overall},
            red_flags=signals,
            strengths=["Diversified risk profile"] if overall < 0.25 else [],
            weaknesses=signals,
            explainability={"why": summary, "top_risks": matrix[:5]},
        )

    def monitor(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        result = self.analyse(payload, **kwargs)
        return {
            "domain": self.domain,
            "subject_id": result.subject_id,
            "signals": result.outputs.get("risk", {}).get("monitoring_signals") or [],
            "risk_matrix_top": (result.outputs.get("risk", {}).get("risk_matrix") or [])[:5],
            "current_score": result.score,
        }
