"""Capital Allocation Intelligence — management capital discipline."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.objects import CapitalAllocationProfile


class CapitalAllocationModel(DomainModel):
    """Teach AGI how management allocates capital and whether it creates value."""

    domain = "capital_allocation"
    version = "1.0.0"
    name = "Capital Allocation Intelligence"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        roic = num(p, "roic", 0.16)
        roce = num(p, "roce", roic)
        incremental_roic = num(p, "incremental_roic", roic * 0.9)
        reinvestment = num(p, "organic_reinvestment_pct", 0.4)
        acquisitions = num(p, "acquisitions_pct", 0.1)
        buybacks = num(p, "buybacks_pct", 0.15)
        dividends = num(p, "dividends_pct", 0.25)
        debt_reduction = num(p, "debt_reduction_pct", 0.1)
        wacc = num(p, "wacc", 0.11)

        value_spread = roic - wacc
        score = clamp(0.5 + value_spread * 2 + 0.1 * (1 if incremental_roic >= wacc else -1))
        if acquisitions > 0.35 and incremental_roic < wacc:
            score = clamp(score - 0.15)
        discipline = "disciplined" if score >= 0.65 and value_spread > 0 else "mixed" if score >= 0.45 else "value_destructive"
        value_creation = "creating" if value_spread > 0.03 else "neutral" if value_spread > 0 else "destroying"

        decisions = [
            {"use": "organic_reinvestment", "weight": reinvestment},
            {"use": "dividends", "weight": dividends},
            {"use": "buybacks", "weight": buybacks},
            {"use": "acquisitions", "weight": acquisitions},
            {"use": "debt_reduction", "weight": debt_reduction},
        ]
        timeline = list(p.get("timeline") or [{"at": "TTM", "decision": "allocation_mix", "roic": roic}])
        summary = (
            f"{sid} capital allocation is {discipline}. ROIC {roic:.1%} vs WACC {wacc:.1%} ({value_creation})."
        )
        profile = CapitalAllocationProfile(
            subject_id=sid,
            capital_allocation_score=round(score, 4),
            management_discipline=discipline,
            value_creation=value_creation,
            roic=roic,
            roce=roce,
            historical_decisions=decisions,
            timeline=timeline,
            version=self.version,
        )
        return AnalysisResult(
            object_type="CapitalAllocationProfile",
            object_id=new_id("cap"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(score, 4),
            label=discipline,
            confidence=0.68,
            summary=summary,
            outputs={"capital_allocation": profile.to_dict(), "incremental_roic": incremental_roic},
            strengths=["ROIC above WACC"] if value_spread > 0 else [],
            weaknesses=["Acquisitive with weak incremental ROIC"] if acquisitions > 0.35 and incremental_roic < wacc else [],
            timeline=timeline,
            explainability={"why": summary, "uses_of_cash": decisions, "value_spread": value_spread},
        )
