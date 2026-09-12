"""Business Model Intelligence — how companies make money."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.objects import BusinessModelProfile


class BusinessModel(DomainModel):
    """Teach AGI operating models, revenue/cost drivers and business quality."""

    domain = "business"
    version = "1.0.0"
    name = "Business Model Intelligence"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)

        recurring = num(p, "recurring_revenue_share", 0.4)
        concentration = num(p, "customer_concentration", 0.25)
        asset_intensity = num(p, "asset_intensity", 0.4)
        capital_intensity = num(p, "capital_intensity", 0.35)
        switching_costs = num(p, "switching_costs", 0.5)
        network_effects = num(p, "network_effects", 0.2)
        pricing_power = num(p, "pricing_power", 0.5)
        streams = list(p.get("revenue_streams") or ["core_operations"])
        segments = list(p.get("segments") or ["core"])
        distribution = str(p.get("distribution") or "direct")
        customer_types = list(p.get("customer_types") or ["enterprise"])

        strengths: list[str] = []
        weaknesses: list[str] = []
        if recurring >= 0.6:
            strengths.append("High recurring revenue share")
        if switching_costs >= 0.6:
            strengths.append("Material switching costs")
        if network_effects >= 0.5:
            strengths.append("Network effects support defensibility")
        if pricing_power >= 0.6:
            strengths.append("Evidence of pricing power")
        if concentration >= 0.4:
            weaknesses.append("Elevated customer concentration")
        if capital_intensity >= 0.7:
            weaknesses.append("Capital intensive operating model")
        if asset_intensity >= 0.7:
            weaknesses.append("High asset intensity")

        quality = clamp(
            0.25 * recurring
            + 0.2 * switching_costs
            + 0.15 * network_effects
            + 0.2 * pricing_power
            + 0.1 * (1.0 - concentration)
            + 0.1 * (1.0 - capital_intensity)
        )
        label = "high_quality" if quality >= 0.7 else "solid" if quality >= 0.5 else "challenged"

        revenue_graph = [
            {"driver": "pricing", "weight": round(pricing_power, 3)},
            {"driver": "volume", "weight": round(1.0 - pricing_power, 3)},
            {"driver": "recurring_mix", "weight": round(recurring, 3)},
        ]
        cost_graph = [
            {"driver": "fixed_opex", "weight": round(num(p, "operating_leverage", 0.5), 3)},
            {"driver": "variable_cogs", "weight": round(1.0 - num(p, "operating_leverage", 0.5), 3)},
            {"driver": "capex", "weight": round(capital_intensity, 3)},
        ]
        summary = (
            f"{sid} business model is {label.replace('_', ' ')}. "
            f"Recurring revenue {recurring:.0%}, customer concentration {concentration:.0%}."
        )
        profile = BusinessModelProfile(
            subject_id=sid,
            business_quality_score=round(quality, 4),
            revenue_streams=streams,
            operating_model_summary=(
                f"Segments={','.join(segments)}; distribution={distribution}; customers={','.join(customer_types)}"
            ),
            revenue_driver_graph=revenue_graph,
            cost_driver_graph=cost_graph,
            strengths=strengths,
            weaknesses=weaknesses,
            recurring_revenue_share=recurring,
            customer_concentration=concentration,
            version=self.version,
        )
        return AnalysisResult(
            object_type="BusinessModelProfile",
            object_id=new_id("biz"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(quality, 4),
            label=label,
            confidence=0.72,
            summary=summary,
            outputs={"business": profile.to_dict()},
            strengths=strengths,
            weaknesses=weaknesses,
            evidence_links=list(p.get("evidence_links") or []),
            explainability={"why": summary, "revenue_drivers": revenue_graph, "cost_drivers": cost_graph},
        )
