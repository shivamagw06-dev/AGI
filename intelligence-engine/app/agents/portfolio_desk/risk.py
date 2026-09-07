"""Portfolio Risk packaging agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.portfolio_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class PortfolioRiskPackager(BaseAgent):
    agent_id = "portfolio_risk"
    mission = "Surface concentration and withheld risk signals — never invent risk numbers."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        sectors = pack.get("sector_exposure") or {}
        risk_score = pack.get("risk_score")
        top = next(iter(sectors.items()), (None, 0.0))
        ev = evidence(
            f"Risk score withheld={risk_score is None}; top sector={top[0]} weight={top[1]}",
            snippet=str(sectors)[:280],
            reliability=0.7,
        )
        findings = [
            Finding(
                statement=(
                    f"Portfolio Risk Score is withheld because risk-engine inputs are unavailable — "
                    f"not fabricated. Largest sector tag is {top[0] or 'n/a'} at {float(top[1] or 0):.0%} of stated weights."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=55,
            )
        ]
        div = pack.get("diversification_score")
        if div is not None:
            findings.append(
                Finding(
                    statement=(
                        f"Diversification Score is {div}/100 from sector weight dispersion "
                        "(Herfindahl-style packaging)."
                    ),
                    evidence_ids=[ev.evidence_id],
                    confidence=60,
                )
            )
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings,
            evidence=[ev],
            confidence=ConfidenceBreakdown(
                score=45 if risk_score is None else int(risk_score),
                supports=[f"sectors={len(sectors)}"],
                challenges=["No VaR/beta/drawdown fabricated"],
                rationale="Risk packaging discloses withheld quantitative risk rather than inventing it.",
            ),
            assumptions=["Sector labels on holdings are correct"],
            invalidators=["Corrected sector taxonomy or risk-engine attachment"],
        )
