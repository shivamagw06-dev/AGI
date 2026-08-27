from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, EvidenceItem, Finding, SourceType


@register_agent
class MarketAnalyst(BaseAgent):
    agent_id = "market_analyst"
    mission = "Read global/overnight market tone from AGIB pre-market cache (licensed proxies)."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pre = await self.agib.pre_market_briefing()
        if not pre:
            evidence = EvidenceItem(
                claim="Pre-market briefing unavailable",
                source_id="agib:pre-market-briefing",
                source_type=SourceType.PRE_MARKET,
                reliability=0.2,
            )
            return AgentOutput(
                agent_id=self.agent_id,
                mission=self.mission,
                findings=[Finding(statement="Market view withheld because pre-market cache is missing.", evidence_ids=[evidence.evidence_id], confidence=25)],
                evidence=[evidence],
                confidence=ConfidenceBreakdown(score=25, supports=[], challenges=["Cache miss"], rationale="Low confidence without overnight market evidence."),
                assumptions=[],
                invalidators=["Successful pre-market briefing fetch"],
            )

        note = pre.get("morningNote") or {}
        markets = ((pre.get("workspace") or {}).get("globalMarkets") or [])[:4]
        evidence_items: list[EvidenceItem] = []
        findings: list[Finding] = []

        outlook = note.get("outlook") or "Selective"
        thesis_ev = EvidenceItem(
            claim=f"Morning outlook: {outlook}",
            source_id="agib:pre-market-briefing",
            source_type=SourceType.PRE_MARKET,
            snippet=str(note.get("executiveThesis") or "")[:300],
            reliability=0.85,
        )
        evidence_items.append(thesis_ev)
        findings.append(
            Finding(
                statement=f"Overnight risk appetite is classified as {outlook} in the AGIB morning note.",
                evidence_ids=[thesis_ev.evidence_id],
                confidence=int(note.get("confidence") or 60),
            )
        )

        for market in markets:
            ev = EvidenceItem(
                claim=f"{market.get('label')}: {market.get('changeLabel')} ({market.get('tone')})",
                source_id=f"agib:global:{market.get('id')}",
                source_type=SourceType.MARKET,
                snippet=market.get("note"),
                reliability=0.8,
            )
            evidence_items.append(ev)
            findings.append(
                Finding(
                    statement=f"{market.get('label')} proxy is {market.get('tone')} at {market.get('changeLabel')}.",
                    evidence_ids=[ev.evidence_id],
                    confidence=70,
                )
            )

        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings[:6],
            evidence=evidence_items,
            confidence=ConfidenceBreakdown(
                score=int(note.get("confidence") or 60),
                supports=[f"Outlook={outlook}", f"Markets={len(markets)}"],
                challenges=["ETF proxies are not futures prints"],
                rationale="Confidence inherits AGIB morning note confidence and proxy coverage.",
            ),
            assumptions=["Global levels are redistribution-friendly API proxies"],
            invalidators=["Sharp reversal in US proxies after cache refresh"],
        )
