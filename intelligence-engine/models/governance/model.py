"""Governance Intelligence — promoter, board, auditor, alignment."""

from __future__ import annotations

from typing import Any

from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.objects import GovernanceProfile


class GovernanceModel(DomainModel):
    """Teach AGI governance quality and agency risk."""

    domain = "governance"
    version = "1.0.0"
    name = "Governance Intelligence"

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)
        promoter = num(p, "promoter_quality", 0.6)
        board = num(p, "board_independence", 0.55)
        auditor = num(p, "auditor_quality", 0.7)
        compensation = num(p, "compensation_alignment", 0.55)
        related_party = num(p, "related_party_risk", 0.25)
        alignment = num(p, "shareholder_alignment", 0.6)
        succession = num(p, "succession_strength", 0.5)
        esg = num(p, "esg_governance", 0.5)

        red_flags = []
        strengths = []
        if related_party >= 0.5:
            red_flags.append("Elevated related-party transaction risk")
        if board < 0.4:
            red_flags.append("Weak board independence")
        if auditor < 0.5:
            red_flags.append("Auditor quality concerns")
        if promoter >= 0.7:
            strengths.append("Strong promoter track record signal")
        if board >= 0.65:
            strengths.append("Credible board independence")
        if alignment >= 0.65:
            strengths.append("Shareholder alignment")

        score = clamp(
            0.2 * promoter
            + 0.2 * board
            + 0.15 * auditor
            + 0.1 * compensation
            + 0.15 * (1.0 - related_party)
            + 0.1 * alignment
            + 0.05 * succession
            + 0.05 * esg
        )
        label = "strong" if score >= 0.7 else "adequate" if score >= 0.5 else "weak"
        timeline = list(p.get("timeline") or [{"at": "current", "event": "governance_assessment", "score": score}])
        summary = f"{sid} governance is {label}."
        profile = GovernanceProfile(
            subject_id=sid,
            governance_score=round(score, 4),
            red_flags=red_flags,
            strengths=strengths,
            timeline=timeline,
            version=self.version,
        )
        return AnalysisResult(
            object_type="GovernanceProfile",
            object_id=new_id("gov"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(score, 4),
            label=label,
            confidence=0.67,
            summary=summary,
            outputs={"governance": profile.to_dict()},
            red_flags=red_flags,
            strengths=strengths,
            timeline=timeline,
            explainability={
                "why": summary,
                "components": {
                    "promoter_quality": promoter,
                    "board_independence": board,
                    "auditor_quality": auditor,
                    "related_party_risk": related_party,
                    "shareholder_alignment": alignment,
                },
            },
        )
