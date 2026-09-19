"""Portfolio summary / workspace packaging agent."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.agents.portfolio_desk._util import evidence, pack_dict
from app.agents.registry import register_agent
from app.schemas.models import AgentOutput, ConfidenceBreakdown, Finding


@register_agent
class PortfolioSummaryPackager(BaseAgent):
    agent_id = "portfolio_summary"
    mission = "Package client/advisor dashboards, timeline, monthly report, and workspace tabs."

    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        pack = pack_dict(context)
        tabs = (pack.get("workspace") or {}).get("tabs") or []
        timeline = pack.get("timeline") or []
        report = pack.get("monthly_report") or {}
        advisor = pack.get("advisor_dashboard") or {}
        ev = evidence(
            f"Workspace tabs={len(tabs)}; timeline points={len(timeline)}",
            snippet=str(report.get("executive_summary") or "")[:280],
        )
        clients = advisor.get("clients_requiring_review") or []
        findings = [
            Finding(
                statement=(
                    f"Portfolio Office workspace ready with tabs: "
                    f"{', '.join(tabs[:6])}{'…' if len(tabs) > 6 else ''}."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=75,
            ),
            Finding(
                statement=str(report.get("executive_summary") or "Monthly report scaffold packaged."),
                evidence_ids=[ev.evidence_id],
                confidence=60,
            ),
            Finding(
                statement=(
                    f"Advisor Action: {len(clients)} client(s) requiring review; "
                    f"{len(advisor.get('high_priority_alerts') or [])} high-priority alerts."
                ),
                evidence_ids=[ev.evidence_id],
                confidence=65,
            ),
        ]
        withheld = pack.get("withheld") or []
        if withheld:
            findings.append(
                Finding(
                    statement=f"Withheld (not fabricated): {withheld[0]}",
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
                score=70,
                supports=["workspace", "monthly_report", "timeline"],
                challenges=list(withheld[:3]),
                rationale=(
                    "Summary packages dashboards and reports from the PortfolioPackage "
                    "without inventing markets data."
                ),
            ),
            assumptions=["Timeline comparisons need stored history"],
            invalidators=["Missing portfolio package in director context"],
        )
