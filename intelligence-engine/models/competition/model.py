"""Competition Intelligence — moats, position, threats."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.objects import CompetitionProfile


class CompetitionModel(DomainModel):
    """Teach AGI why businesses win or lose competitively."""

    domain = "competition"
    version = "1.0.0"
    name = "Competition Intelligence"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        share = num(p, "market_share", 0.15)
        brand = num(p, "brand", 0.5)
        distribution = num(p, "distribution", 0.5)
        pricing_power = num(p, "pricing_power", 0.5)
        switching = num(p, "switching_costs", 0.5)
        technology = num(p, "technology", 0.45)
        cost_leadership = num(p, "cost_leadership", 0.4)
        scale = num(p, "scale_advantage", 0.5)
        entry_barriers = num(p, "entry_barriers", 0.5)
        substitution = num(p, "substitution_risk", 0.4)

        moat = clamp(
            0.15 * brand
            + 0.15 * switching
            + 0.15 * distribution
            + 0.1 * technology
            + 0.1 * cost_leadership
            + 0.15 * scale
            + 0.2 * entry_barriers
        )
        competitive = clamp(0.55 * moat + 0.25 * share * 2 + 0.2 * pricing_power - 0.15 * substitution)
        position = (
            "leader" if competitive >= 0.75 else "strong" if competitive >= 0.6 else "challenger" if competitive >= 0.45 else "weak"
        )
        threats = []
        if substitution >= 0.6:
            threats.append("High substitution risk")
        if entry_barriers < 0.4:
            threats.append("Low entry barriers")
        if share < 0.1:
            threats.append("Limited market share")
        peers = list(p.get("peers") or [])
        peer_rows = [{"symbol": str(x).upper(), "relation": "peer"} for x in peers[:8]]
        summary = f"{sid} competitive position: {position}. Moat strength {moat:.0%}."
        profile = CompetitionProfile(
            subject_id=sid,
            competitive_score=round(competitive, 4),
            moat_strength=round(moat, 4),
            competitive_position=position,
            threats=threats,
            peer_comparison=peer_rows,
            version=self.version,
        )
        return AnalysisResult(
            object_type="CompetitionProfile",
            object_id=new_id("cmp"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(competitive, 4),
            label=position,
            confidence=0.7,
            summary=summary,
            outputs={"competition": profile.to_dict()},
            red_flags=threats,
            strengths=[s for s, v in [("brand", brand), ("switching_costs", switching), ("scale", scale)] if v >= 0.6],
            relationships=[{"from": sid, "to": r["symbol"], "type": "competitor"} for r in peer_rows],
            explainability={
                "why": summary,
                "moat_components": {
                    "brand": brand,
                    "switching_costs": switching,
                    "distribution": distribution,
                    "technology": technology,
                    "cost_leadership": cost_leadership,
                    "scale": scale,
                    "entry_barriers": entry_barriers,
                },
            },
        )
