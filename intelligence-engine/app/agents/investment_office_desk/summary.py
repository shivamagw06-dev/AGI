"""Investment Office workspace + Portfolio Office link summary agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.investment_office_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class InvestmentSummaryPackager(BaseAgent):
    agent_id = "investment_summary"
    mission = "Package Investment Office workspace tabs and Portfolio Office linkage for CIO synthesis."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        tabs = (pack.get("workspace") or {}).get("tabs") or []
        port = pack.get("portfolio_office_link") or {}
        recs = pack.get("recommendations") or []
        reused = pack.get("components_reused") or []
        ev = evidence(
            f"Workspace tabs={len(tabs)}; recommendations={len(recs)}; reused={len(reused)}",
            snippet=", ".join(tabs[:6]),
        )
        findings = [
            Finding(
                statement=f"Investment Office workspace ready: {', '.join(tabs[:5])}{'…' if len(tabs) > 5 else ''}.",
                evidence_ids=[ev.evidence_id],
                confidence=80,
            ),
            Finding(
                statement=(
                    f"Portfolio Office link: {port.get('status')} "
                    f"(health={port.get('health_score')}, recs={port.get('recommendation_count')})."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=65,
            ),
            Finding(
                statement=f"Orchestrates {len(reused)} existing platform components — no duplicate engines.",
                evidence_ids=[ev.evidence_id],
                confidence=85,
            ),
        ]
        if pack.get("withheld"):
            findings.append(
                Finding(
                    statement=f"Withheld (not fabricated): {pack['withheld'][0]}",
                    evidence_ids=[ev.evidence_id],
                    confidence=80,
                )
            )
        return AgentOutput(
            agent_id=self.agent_id,
            mission=self.mission,
            findings=findings,
            evidence=[ev],
            confidence=ConfidenceBreakdown(
                score=75,
                supports=["workspace", "components_reused"],
                challenges=list((pack.get("withheld") or [])[:2]),
                rationale="Summary confirms operational layer packaging without new research engines.",
            ),
            assumptions=["Director attached InvestmentOfficePackage before agent loop"],
            invalidators=["Empty office package"],
        )
