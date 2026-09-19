"""Forecasting Knowledge — assumption quality frameworks for FLE (does not forecast)."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id


class ForecastingKnowledgeModel(DomainModel):
    """Help FLE/IRP judge forecast assumption quality and horizon discipline."""

    domain = "forecasting"
    version = "1.0.0"
    name = "Forecasting Knowledge"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        horizon = num(p, "horizon_days", 365)
        confidence = num(p, "forecast_confidence", 0.6)
        has_assumptions = bool(p.get("assumptions") or p.get("assumption_count"))
        has_evidence = bool(p.get("evidence_ids") or p.get("evidence_links"))
        calibration = str(p.get("calibration_label") or "unknown").lower()
        base = 0.4
        if has_assumptions:
            base += 0.2
        if has_evidence:
            base += 0.2
        if "well" in calibration:
            base += 0.15
        if horizon > 900:
            base -= 0.1
        score = clamp(base * 0.7 + confidence * 0.3)
        label = "robust" if score >= 0.7 else "usable" if score >= 0.5 else "fragile"
        notes = []
        if not has_assumptions:
            notes.append("Forecast lacks explicit assumptions")
        if not has_evidence:
            notes.append("Forecast lacks evidence linkage")
        if horizon > 900:
            notes.append("Long horizon — widen uncertainty")
        summary = f"Forecast assumption quality for {sid} is {label}."
        return AnalysisResult(
            object_type="ForecastAssumptionReview",
            object_id=new_id("fca"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(score, 4),
            label=label,
            confidence=0.65,
            summary=summary,
            outputs={
                "horizon_days": horizon,
                "recommended_uncertainty_band": 0.1 if score >= 0.7 else 0.2 if score >= 0.5 else 0.35,
                "requires_assumptions": True,
                "requires_evidence": True,
            },
            red_flags=notes,
            explainability={"why": summary, "checks": {"assumptions": has_assumptions, "evidence": has_evidence, "calibration": calibration}},
        )
