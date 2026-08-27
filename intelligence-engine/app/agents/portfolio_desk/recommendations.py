"""Portfolio recommendation packaging agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.portfolio_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class PortfolioRecommendationPackager(BaseAgent):
    agent_id = "portfolio_recommendations"
    mission = "Package Review/Research/Monitor recommendations with evidence — never Buy/Sell/Execute."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        recs = pack.get("recommendations") or []
        action = pack.get("action_center") or {}
        high = action.get("high") or []
        ev = evidence(
            f"{len(recs)} portfolio recommendations; {len(high)} high priority",
            snippet="; ".join(r.get("title", "") for r in recs[:4]),
        )
        findings: list[Finding] = [
            Finding(
                statement=(
                    f"Action Center has {len(high)} high, {len(action.get('medium') or [])} medium, "
                    f"{len(action.get('low') or [])} low priority items. Language is Review/Research/Monitor only."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=70,
            )
        ]
        for rec in recs[:4]:
            findings.append(
                Finding(
                    statement=f"{rec.get('verb')} — {rec.get('title')}: {rec.get('reason')}",
                    evidence_ids=[ev.evidence_id],
                    confidence=int(rec.get("confidence") or 55),
                )
            )
        if not recs:
            findings.append(
                Finding(
                    statement="No recommendations generated — insufficient concentration or research signals.",
                    evidence_ids=[ev.evidence_id],
                    confidence=50,
                )
            )
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings[:8],
            evidence=[ev],
            confidence=ConfidenceBreakdown(
                score=65 if recs else 45,
                supports=[f"recommendations={len(recs)}"],
                challenges=["Not trade instructions"],
                rationale="Recommendations are research actions derived from stated weights and research coverage.",
            ),
            assumptions=["Forbidden trade verbs are filtered"],
            invalidators=["Updated holdings that remove concentration"],
        )
