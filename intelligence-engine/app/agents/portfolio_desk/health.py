"""Portfolio Health packaging agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.portfolio_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class PortfolioHealthPackager(BaseAgent):
    agent_id = "portfolio_health"
    mission = "Package Portfolio Health Score and executive health summary from ingested holdings."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        health = pack.get("health_score")
        summary = pack.get("health_summary") or {}
        portfolio = pack.get("portfolio") or {}
        n = len(portfolio.get("holdings") or [])
        ev = evidence(
            f"Portfolio health_score={health} across {n} holdings",
            snippet=str(summary.get("portfolio_health") or "")[:280],
        )
        strengths = summary.get("strengths") or []
        weaknesses = summary.get("weaknesses") or []
        findings = [
            Finding(
                statement=(
                    f"Portfolio Health Score is {health if health is not None else 'withheld'} because "
                    "coverage and diversification of stated weights were packaged without fabricating returns."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=health if isinstance(health, int) else 40,
            )
        ]
        if strengths:
            findings.append(
                Finding(
                    statement=f"Strength: {strengths[0]}",
                    evidence_ids=[ev.evidence_id],
                    confidence=60,
                )
            )
        if weaknesses:
            findings.append(
                Finding(
                    statement=f"Weakness: {weaknesses[0]}",
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
                score=health if isinstance(health, int) else 40,
                supports=[f"holdings={n}", f"health_score={health}"],
                challenges=["Returns and live NAV not used"],
                rationale="Health score combines research coverage and sector diversification of stated weights only.",
            ),
            assumptions=["Weights come from ingestion; equal-weight is disclosed when applied."],
            invalidators=["Material rebalance not reflected in the snapshot"],
        )
