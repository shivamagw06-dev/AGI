"""Decision Intelligence — institutional investment framework over FIML outputs."""

from __future__ import annotations

from typing import Any

from models.accounting.model import AccountingModel
from models.base import AnalysisResult, DomainModel, clamp, new_id, num, subject_id
from models.business.model import BusinessModel
from models.capital_allocation.model import CapitalAllocationModel
from models.competition.model import CompetitionModel
from models.economics.model import EconomicModel
from models.governance.model import GovernanceModel
from models.industry.model import IndustryEconomicsModel
from models.macro.model import MacroModel
from models.objects import DecisionProfile
from models.risk.model import RiskModel
from models.valuation.model import ValuationKnowledgeModel


class DecisionModel(DomainModel):
    """Combine domain models into an explainable institutional decision profile."""

    domain = "decision"
    version = "1.0.0"
    name = "Decision Intelligence"

    def __init__(self) -> None:
        self.accounting = AccountingModel()
        self.business = BusinessModel()
        self.industry = IndustryEconomicsModel()
        self.competition = CompetitionModel()
        self.capital = CapitalAllocationModel()
        self.governance = GovernanceModel()
        self.risk = RiskModel()
        self.economics = EconomicModel()
        self.macro = MacroModel()
        self.valuation = ValuationKnowledgeModel()

    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        p = dict(payload or {})
        p.update({k: v for k, v in kwargs.items() if v is not None})
        sid = subject_id(p)

        parts = {
            "accounting": self.accounting.analyse(p),
            "business": self.business.analyse(p),
            "industry": self.industry.analyse(p),
            "competition": self.competition.analyse(p),
            "capital_allocation": self.capital.analyse(p),
            "governance": self.governance.analyse(p),
            "risk": self.risk.analyse(p),
            "economics": self.economics.analyse(p),
            "macro": self.macro.analyse(p),
            "valuation": self.valuation.analyse(p),
        }

        quality = clamp(
            0.15 * parts["accounting"].score
            + 0.15 * parts["business"].score
            + 0.15 * parts["competition"].score
            + 0.1 * parts["capital_allocation"].score
            + 0.1 * parts["governance"].score
            + 0.15 * parts["risk"].score
            + 0.1 * parts["macro"].score
            + 0.1 * parts["industry"].score
        )

        mos = num(p, "margin_of_safety", num(p, "discount_premium_pct", 0.0) / 100.0)
        # If mos provided as percent > 1, normalise
        if abs(mos) > 1.5:
            mos = mos / 100.0
        expected_return = clamp(0.08 + mos * 0.5 + (quality - 0.5) * 0.2, -0.3, 0.4)
        expected_downside = clamp(0.25 - parts["risk"].score * 0.15 + (1.0 - quality) * 0.1, 0.05, 0.6)
        conviction = clamp(0.4 * quality + 0.3 * clamp(mos + 0.2) + 0.3 * parts["governance"].score)

        red = []
        for k, r in parts.items():
            red.extend([f"[{k}] {x}" for x in r.red_flags[:2]])
        catalysts = list(p.get("catalysts") or [])
        if parts["macro"].label == "tailwind":
            catalysts.append("Supportive macro transmission")
        if parts["capital_allocation"].label == "disciplined":
            catalysts.append("Disciplined capital allocation")

        # Action policy — institutional, refuse-friendly
        data_grade = str(p.get("data_quality") or "B").upper()
        if data_grade in {"SYNTHETIC", "C"} and not bool(p.get("allow_weak_data")):
            action = "refuse_insufficient_data"
        elif mos >= 0.2 and quality >= 0.65 and parts["risk"].label != "high":
            action = "buy"
        elif mos >= 0.05 and quality >= 0.55:
            action = "wait"
        elif quality < 0.45 or parts["risk"].label == "high":
            action = "avoid"
        else:
            action = "wait"

        confidence = clamp(
            0.35
            + 0.1 * sum(1 for r in parts.values() if r.confidence >= 0.65) / max(1, len(parts))
            + 0.2 * (0 if action == "refuse_insufficient_data" else conviction)
        )
        summary = (
            f"{sid}: suggested action={action}. Investment quality {quality:.0%}, "
            f"conviction {conviction:.0%}, MoS {mos:.0%}."
        )
        profile = DecisionProfile(
            subject_id=sid,
            investment_quality=round(quality, 4),
            conviction=round(conviction, 4),
            expected_return=round(expected_return, 4),
            expected_downside=round(expected_downside, 4),
            margin_of_safety=round(mos, 4),
            suggested_action=action,
            confidence=round(confidence, 4),
            key_risks=red[:8],
            catalysts=catalysts[:8],
            explainability={
                "why": summary,
                "component_scores": {k: v.score for k, v in parts.items()},
                "valuation_primary": parts["valuation"].label,
                "action_policy": "quality_mos_risk_data_grade",
            },
            version=self.version,
        )
        return AnalysisResult(
            object_type="DecisionProfile",
            object_id=new_id("dec"),
            domain=self.domain,
            model_version=self.version,
            subject_id=sid,
            score=round(quality, 4),
            label=action,
            confidence=round(confidence, 4),
            summary=summary,
            outputs={
                "decision": profile.to_dict(),
                "components": {k: v.to_dict() for k, v in parts.items()},
            },
            red_flags=red[:8],
            strengths=[s for r in parts.values() for s in r.strengths[:1]][:6],
            weaknesses=[w for r in parts.values() for w in r.weaknesses[:1]][:6],
            evidence_links=list(p.get("evidence_links") or []),
            explainability=profile.explainability,
        )
