from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, EvidenceItem, Finding, SourceType


@register_agent
class RiskManager(BaseAgent):
    agent_id = "risk_manager"
    mission = "Identify invalidators, scenario risks, and confidence challenges from AGIB desks."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        macro = await self.agib.macro_briefing()
        pre = await self.agib.pre_market_briefing()
        risks = ((macro or {}).get("chiefEconomistBrief") or {}).get("keyRisks") or []
        scenarios = ((pre or {}).get("morningNote") or {}).get("scenarios") or {}
        evidence_items: list[EvidenceItem] = []
        findings: list[Finding] = []

        for risk in risks[:4]:
            ev = EvidenceItem(
                claim=f"Risk: {risk.get('label')} ({risk.get('level')})",
                source_id="agib:macro-briefing",
                source_type=SourceType.MACRO,
                snippet=risk.get("why"),
                reliability=0.8,
            )
            evidence_items.append(ev)
            findings.append(
                Finding(
                    statement=f"{risk.get('label')} is {risk.get('level')} because {risk.get('why')}",
                    evidence_ids=[ev.evidence_id],
                    confidence=65,
                    is_scenario=True,
                )
            )

        for key in ("base", "bull", "bear"):
            case = scenarios.get(key) or {}
            if not case:
                continue
            ev = EvidenceItem(
                claim=f"Scenario {key}: {case.get('label')} ({case.get('probability')}%)",
                source_id="agib:pre-market-briefing",
                source_type=SourceType.PRE_MARKET,
                snippet=case.get("detail"),
                reliability=0.75,
            )
            evidence_items.append(ev)
            findings.append(
                Finding(
                    statement=f"{key.title()} case ({case.get('probability')}%): {case.get('detail')}",
                    evidence_ids=[ev.evidence_id],
                    confidence=int(case.get("probability") or 50),
                    is_scenario=True,
                )
            )

        if not evidence_items:
            ev = EvidenceItem(
                claim="Risk package empty in caches",
                source_id="internal:risk",
                source_type=SourceType.INTERNAL,
                reliability=0.3,
            )
            evidence_items = [ev]
            findings = [Finding(statement="Risk manager could not locate cached risk/scenario blocks.", evidence_ids=[ev.evidence_id], confidence=30, is_scenario=True)]

        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings[:8],
            evidence=evidence_items,
            confidence=ConfidenceBreakdown(
                score=62 if risks or scenarios else 30,
                supports=[f"risks={len(risks)}", f"scenarios={len(scenarios)}"],
                challenges=["Scenario probabilities are not guarantees"],
                rationale="Risk confidence reflects completeness of AGIB risk and scenario caches.",
            ),
            assumptions=["Scenario probabilities are directional planning aids"],
            invalidators=["Risk that was not in cache but materializes into the open"],
        )
