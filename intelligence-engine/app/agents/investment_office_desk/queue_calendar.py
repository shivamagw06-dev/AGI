"""Research queue + calendar packaging agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.investment_office_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class InvestmentQueueCalendarPackager(BaseAgent):
    agent_id = "investment_queue_calendar"
    mission = "Package Research Queue priorities and Investment Calendar — withhold invented dates."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        queue = pack.get("research_queue") or []
        calendar = pack.get("calendar") or []
        high = [q for q in queue if q.get("priority") == "high"]
        live_cal = [c for c in calendar if c.get("status") != "withheld"]
        ev = evidence(
            f"Queue items={len(queue)} high={len(high)}; calendar live={len(live_cal)}",
            snippet="; ".join(q.get("title", "") for q in queue[:4]),
        )
        findings = [
            Finding(
                statement=(
                    f"Research Queue: {len(high)} high, "
                    f"{sum(1 for q in queue if q.get('priority')=='medium')} medium, "
                    f"{sum(1 for q in queue if q.get('priority')=='low')} low priority items."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=70,
            )
        ]
        for q in high[:3]:
            findings.append(
                Finding(
                    statement=f"High — {q.get('title')}: {q.get('reason')}",
                    evidence_ids=[ev.evidence_id],
                    confidence=int(q.get("confidence") or 55),
                )
            )
        findings.append(
            Finding(
                statement=(
                    f"Investment Calendar tracks earnings/RBI/Fed/inflation/GDP and corporate events; "
                    f"{len(live_cal)} evidenced, remainder withheld without dates."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=60,
            )
        )
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings[:8],
            evidence=[ev],
            confidence=ConfidenceBreakdown(
                score=65 if queue else 45,
                supports=[f"queue={len(queue)}", f"calendar_live={len(live_cal)}"],
                challenges=["Event dates not invented"],
                rationale="Prioritisation uses watchlist/portfolio/prior-run signals only.",
            ),
            assumptions=["Forbidden trade verbs filtered from queue titles"],
            invalidators=["Updated research that clears high-priority items"],
        )
