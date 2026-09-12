from __future__ import annotations

from app.schemas.models import AgentOutput, DebatePackage, DebatePosition, EvidenceItem


class DebateEngine:
    """Surface bull/base/bear tensions from analyst packages without inventing facts."""

    def debate(self, outputs: list[AgentOutput], evidence: list[EvidenceItem]) -> DebatePackage:
        bull: list[str] = []
        bear: list[str] = []
        base: list[str] = []
        bull_ids: list[str] = []
        bear_ids: list[str] = []
        base_ids: list[str] = []

        for output in outputs:
            for finding in output.findings:
                text = finding.statement
                lower = text.lower()
                if finding.is_scenario or any(k in lower for k in ("risk", "bear", "weak", "threat", "challeng")):
                    bear.append(text)
                    bear_ids.extend(finding.evidence_ids)
                elif any(k in lower for k in ("bull", "improv", "strong", "support", "positive", "resilient")):
                    bull.append(text)
                    bull_ids.extend(finding.evidence_ids)
                else:
                    base.append(text)
                    base_ids.extend(finding.evidence_ids)

        unresolved = []
        if bull and bear:
            unresolved.append("Bullish and bearish analyst findings coexist; CIO must weigh transmission, not average them.")

        summary = (
            f"Debate package assembled from {len(outputs)} agents and {len(evidence)} evidence items. "
            f"Bull points={len(bull)}, base={len(base)}, bear={len(bear)}."
        )
        return DebatePackage(
            summary=summary,
            positions=[
                DebatePosition(side="bull", points=bull[:6], evidence_ids=list(dict.fromkeys(bull_ids))[:12]),
                DebatePosition(side="base", points=base[:6], evidence_ids=list(dict.fromkeys(base_ids))[:12]),
                DebatePosition(side="bear", points=bear[:6], evidence_ids=list(dict.fromkeys(bear_ids))[:12]),
            ],
            unresolved_conflicts=unresolved,
        )
