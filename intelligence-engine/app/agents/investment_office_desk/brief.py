"""Daily CIO brief packaging agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.investment_office_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class InvestmentBriefPackager(BaseAgent):
    agent_id = "investment_brief"
    mission = "Package the Daily CIO Brief from AGIB caches and Investment Office queue — no trade calls."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        brief = pack.get("daily_brief") or {}
        ev = evidence(
            "Daily CIO Brief packaged",
            snippet=str(brief.get("executive_summary") or "")[:280],
        )
        story = brief.get("todays_market_story")
        story_txt = story if isinstance(story, str) else (story or {}).get("note") or "Market story withheld"
        findings = [
            Finding(
                statement=str(brief.get("executive_summary") or "Daily brief scaffold packaged."),
                evidence_ids=[ev.evidence_id],
                confidence=int(pack.get("confidence") or 50),
            ),
            Finding(
                statement=f"Today's Market Story: {str(story_txt)[:220]}",
                evidence_ids=[ev.evidence_id],
                confidence=55,
            ),
            Finding(
                statement=(
                    f"Research priorities: {', '.join(str(x) for x in (brief.get('research_priorities') or [])[:5]) or 'none yet'}."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=60,
            ),
        ]
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings,
            evidence=[ev],
            confidence=ConfidenceBreakdown(
                score=int(pack.get("confidence") or 50),
                supports=["daily_brief", "research_queue"],
                challenges=list((brief.get("withheld") or pack.get("withheld") or [])[:3]),
                rationale="Brief packages cache-backed market story and prioritised research without inventing trades.",
            ),
            assumptions=["AGIB caches and queue inputs are the only factual sources"],
            invalidators=["Stale caches or missing watchlist/portfolio context"],
        )
