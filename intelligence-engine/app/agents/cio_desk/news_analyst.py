from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, EvidenceItem, Finding, SourceType


@register_agent
class NewsAnalyst(BaseAgent):
    agent_id = "news_analyst"
    mission = "Extract why-it-matters from AGIB news/context caches — not headline dumps."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        briefing = await self.agib.market_briefing()
        pre = await self.agib.pre_market_briefing()
        articles = (briefing or {}).get("articles") or []
        overnight = ((pre or {}).get("workspace") or {}).get("overnightNews") or []

        evidence_items: list[EvidenceItem] = []
        findings: list[Finding] = []

        for item in overnight[:3]:
            ev = EvidenceItem(
                claim=item.get("headline") or "Overnight development",
                source_id="agib:pre-market-briefing",
                source_type=SourceType.PRE_MARKET,
                snippet=item.get("whyItMatters"),
                url=item.get("url"),
                reliability=0.75,
            )
            evidence_items.append(ev)
            findings.append(
                Finding(
                    statement=f"{item.get('headline')}: {item.get('whyItMatters')}",
                    evidence_ids=[ev.evidence_id],
                    confidence=70 if item.get("importance") == "HIGH" else 55,
                )
            )

        for article in articles[:2]:
            ev = EvidenceItem(
                claim=article.get("title") or "Market news item",
                source_id="agib:market-briefing",
                source_type=SourceType.NEWS,
                snippet=article.get("summary"),
                url=article.get("url"),
                reliability=0.7,
            )
            evidence_items.append(ev)
            findings.append(
                Finding(
                    statement=f"News item ({article.get('importance') or 'impact n/a'}): {article.get('title')}",
                    evidence_ids=[ev.evidence_id],
                    confidence=60,
                )
            )

        if not evidence_items:
            ev = EvidenceItem(
                claim="No news evidence in AGIB caches for this run",
                source_id="agib:news",
                source_type=SourceType.NEWS,
                reliability=0.3,
            )
            evidence_items = [ev]
            findings = [Finding(statement="News analyst found no cached headlines to interpret.", evidence_ids=[ev.evidence_id], confidence=30)]

        score = 68 if overnight or articles else 30
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings[:5],
            evidence=evidence_items,
            confidence=ConfidenceBreakdown(
                score=score,
                supports=[f"{len(overnight)} overnight items", f"{len(articles)} briefing articles"],
                challenges=[] if evidence_items else ["Empty news cache"],
                rationale="Confidence tracks availability and importance tagging in AGIB news caches.",
            ),
            assumptions=["Cached headlines are source-linked and not fabricated"],
            invalidators=["Material headline missing from cache that changes open thesis"],
        )
