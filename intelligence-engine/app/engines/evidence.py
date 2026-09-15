from __future__ import annotations

from app.schemas.models import AgentOutput, EvidenceItem


class EvidenceEngine:
    """Normalize, dedupe, and validate evidence packages."""

    def collect(self, outputs: list[AgentOutput]) -> list[EvidenceItem]:
        seen: dict[str, EvidenceItem] = {}
        for output in outputs:
            for item in output.evidence:
                key = f"{item.source_id}|{item.claim.strip().lower()}"
                existing = seen.get(key)
                if not existing or item.reliability > existing.reliability:
                    seen[key] = item
        return list(seen.values())

    def validate_outputs(self, outputs: list[AgentOutput]) -> list[str]:
        errors: list[str] = []
        for output in outputs:
            if not output.evidence:
                errors.append(f"{output.agent_id}: missing evidence")
            if output.confidence is None:
                errors.append(f"{output.agent_id}: missing confidence")
            known = {e.evidence_id for e in output.evidence}
            for finding in output.findings:
                if not finding.evidence_ids:
                    errors.append(f"{output.agent_id}: finding without citations")
                elif any(eid not in known for eid in finding.evidence_ids):
                    errors.append(f"{output.agent_id}: finding cites unknown evidence")
        return errors
