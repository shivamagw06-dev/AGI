from __future__ import annotations

from app.schemas.models import AgentOutput, EvidenceItem, InstitutionalReport


class CitationEngine:
    """Map report claims to evidence ids."""

    def build_citation_map(
        self,
        outputs: list[AgentOutput],
        evidence: list[EvidenceItem],
    ) -> dict[str, list[str]]:
        citations: dict[str, list[str]] = {}
        known = {item.evidence_id for item in evidence}
        for output in outputs:
            for finding in output.findings:
                key = finding.statement[:180]
                ids = [eid for eid in finding.evidence_ids if eid in known]
                if ids:
                    citations[key] = ids
        return citations

    def attach(self, report: InstitutionalReport, citations: dict[str, list[str]]) -> InstitutionalReport:
        report.citations = citations
        return report
