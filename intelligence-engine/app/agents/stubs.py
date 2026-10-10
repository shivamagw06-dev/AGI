from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, EvidenceItem, Finding, SourceType


@register_agent
class SmokeAnalyst(BaseAgent):
    agent_id = "smoke_analyst"
    mission = "Validate the Intelligence Core pipeline with cited AGIB-cache or internal evidence."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        macro = await self.agib.macro_briefing()
        if macro:
            outlook = (macro.get("chiefEconomistBrief") or {}).get("outlook") or "data-dependent"
            evidence = EvidenceItem(
                claim=f"AGI macro desk outlook is {outlook}",
                source_id="agib:macro-briefing",
                source_type=SourceType.MACRO,
                snippet=str((macro.get("chiefEconomistBrief") or {}).get("executiveThesis") or "")[:280],
                reliability=0.85,
            )
            finding = Finding(
                statement=f"Smoke analyst confirms macro cache is reachable and outlook reads {outlook}.",
                evidence_ids=[evidence.evidence_id],
                confidence=80,
            )
            return AgentOutput(
                agent_id=self.agent_id,
                mission=self.mission,
                findings=[finding],
                evidence=[evidence],
                confidence=ConfidenceBreakdown(
                    score=80,
                    supports=["Macro briefing endpoint responded"],
                    challenges=[],
                    rationale="Confidence is high because AGIB macro cache returned a structured briefing.",
                ),
                assumptions=["Macro cache reflects the latest scheduled refresh."],
                invalidators=["Macro endpoint unavailable or empty payload"],
            )

        evidence = EvidenceItem(
            claim="AGIB macro cache unavailable; smoke run uses internal probe evidence",
            source_id="internal:smoke",
            source_type=SourceType.INTERNAL,
            snippet="macro-briefing returned null",
            reliability=0.4,
        )
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=[
                Finding(
                    statement="Smoke pipeline operates, but AGIB macro cache was unavailable during this run.",
                    evidence_ids=[evidence.evidence_id],
                    confidence=45,
                )
            ],
            evidence=[evidence],
            confidence=ConfidenceBreakdown(
                score=45,
                supports=["Engine orchestration path executed"],
                challenges=["Upstream AGIB cache miss"],
                rationale="Moderate confidence because the engine ran but supporting market evidence was missing.",
            ),
            assumptions=[],
            invalidators=["Successful AGIB macro-briefing fetch"],
        )
