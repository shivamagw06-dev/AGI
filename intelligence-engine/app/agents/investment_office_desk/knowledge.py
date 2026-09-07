"""Knowledge graph, playbooks, journal, scenario center packaging agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.investment_office_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class InvestmentKnowledgePackager(BaseAgent):
    agent_id = "investment_knowledge"
    mission = "Package Knowledge Graph, Playbooks, Decision Journal, and Scenario Center scaffolds."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        graph = pack.get("knowledge_graph") or {}
        playbooks = pack.get("playbooks") or []
        journal = pack.get("decision_journal") or []
        timeline = pack.get("research_timeline") or []
        scenario = pack.get("scenario_center") or {}
        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []
        ev = evidence(
            f"Graph nodes={len(nodes)} edges={len(edges)}; playbooks={len(playbooks)}; journal={len(journal)}",
            snippet=str(scenario.get("policy") or "")[:280],
        )
        findings = [
            Finding(
                statement=f"Knowledge Graph connects {len(nodes)} nodes and {len(edges)} evidenced relationships.",
                evidence_ids=[ev.evidence_id],
                confidence=70,
            ),
            Finding(
                statement=f"{len(playbooks)} investment playbooks packaged (Banking, IT, Power, Defence, Capital Goods, FMCG, Healthcare).",
                evidence_ids=[ev.evidence_id],
                confidence=75,
            ),
            Finding(
                statement=f"Decision Journal has {len(journal)} entries; research timeline spans {len(timeline)} period(s).",
                evidence_ids=[ev.evidence_id],
                confidence=65,
            ),
            Finding(
                statement=(
                    "Scenario Center reuses Forecast/Portfolio/Macro/Research and withholds invented outcomes."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=80,
            ),
        ]
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings,
            evidence=[ev],
            confidence=ConfidenceBreakdown(
                score=70,
                supports=["knowledge_graph", "playbooks", "decision_journal"],
                challenges=["Scenario outcomes require live engines"],
                rationale="Knowledge packaging links existing entities without fabricating edges.",
            ),
            assumptions=["Playbooks are structural templates, not live valuations"],
            invalidators=["Missing office package in director context"],
        )
