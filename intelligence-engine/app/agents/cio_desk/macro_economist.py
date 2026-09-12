from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, EvidenceItem, Finding, SourceType


@register_agent
class MacroEconomist(BaseAgent):
    agent_id = "macro_economist"
    mission = "Interpret macro transmission for India using AGIB macro cache only."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        data = await self.agib.macro_briefing()
        if not data:
            evidence = EvidenceItem(
                claim="Macro briefing unavailable from AGIB cache",
                source_id="agib:macro-briefing",
                source_type=SourceType.MACRO,
                reliability=0.2,
            )
            return AgentOutput(
                agent_id=self.agent_id,
                mission=self.mission,
                findings=[Finding(statement="Macro view withheld because cache evidence is missing.", evidence_ids=[evidence.evidence_id], confidence=25)],
                evidence=[evidence],
                confidence=ConfidenceBreakdown(score=25, supports=[], challenges=["Cache miss"], rationale="Low confidence without macro evidence."),
                assumptions=[],
                invalidators=["Successful macro-briefing fetch"],
            )

        brief = data.get("chiefEconomistBrief") or {}
        outlook = brief.get("outlook") or "data-dependent"
        thesis = brief.get("executiveThesis") or brief.get("confidenceRationale") or "Macro thesis present in cache."
        evidence = EvidenceItem(
            claim=f"Macro outlook: {outlook}",
            source_id="agib:macro-briefing",
            source_type=SourceType.MACRO,
            snippet=str(thesis)[:320],
            reliability=0.85,
        )
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=[
                Finding(
                    statement=f"Macro desk reads the backdrop as {outlook} because AGIB cached thesis emphasizes transmission over raw prints.",
                    evidence_ids=[evidence.evidence_id],
                    confidence=int(brief.get("confidence") or 60),
                )
            ],
            evidence=[evidence],
            confidence=ConfidenceBreakdown(
                score=int(brief.get("confidence") or 60),
                supports=[f"Outlook={outlook}"],
                challenges=list((brief.get("reliability") or {}).get("missingInputs") or [])[:3],
                rationale=str(brief.get("confidenceRationale") or "Derived from AGIB macro confidence block."),
            ),
            assumptions=["Macro cache freshness is acceptable for this session"],
            invalidators=["Oil/policy shock that invalidates cached transmission map"],
        )
