from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.logging import get_logger
from app.schemas.models import AgentOutput, ConfidenceBreakdown, EvidenceItem, Finding, SourceType, new_id
from app.tools.agib_client import AgibClient

log = get_logger(__name__)


class BaseAgent(ABC):
    agent_id: str
    mission: str

    def __init__(self, agib: AgibClient | None = None):
        self.agib = agib or AgibClient()

    @abstractmethod
    async def analyze(self, context: dict[str, Any]) -> AgentOutput:
        raise NotImplementedError

    async def run(self, context: dict[str, Any]) -> AgentOutput:
        run_id = context.get("run_id")
        log.info("agent_start", extra={"agent_id": self.agent_id, "run_id": run_id})
        try:
            output = await self.analyze(context)
            if output.agent_id != self.agent_id:
                output.agent_id = self.agent_id
            if not output.mission:
                output.mission = self.mission
            log.info(
                "agent_complete",
                extra={"agent_id": self.agent_id, "run_id": run_id, "findings": len(output.findings)},
            )
            return output
        except Exception as exc:
            log.exception("agent_failed", extra={"agent_id": self.agent_id, "run_id": run_id})
            # Soft failure package — Director decides whether to continue
            evidence = EvidenceItem(
                claim=f"Agent {self.agent_id} failed: {exc}",
                source_id="internal:agent_error",
                source_type=SourceType.INTERNAL,
                snippet=str(exc),
                reliability=0.2,
            )
            return AgentOutput(
                agent_id=self.agent_id,
                mission=self.mission,
                findings=[
                    Finding(
                        statement=f"{self.agent_id} could not complete analysis because {exc}",
                        evidence_ids=[evidence.evidence_id],
                        is_scenario=False,
                        confidence=20,
                    )
                ],
                evidence=[evidence],
                confidence=ConfidenceBreakdown(
                    score=20,
                    supports=[],
                    challenges=[str(exc)],
                    rationale="Agent failed; confidence is low until the tool/data path is restored.",
                ),
                assumptions=[],
                invalidators=["Successful agent re-run with valid evidence"],
                raw_trace_ref=new_id("trace_"),
            )
