from __future__ import annotations

from app.schemas.models import AgentOutput, ConfidenceBreakdown, EvidenceItem


class ConfidenceEngine:
    """Combine agent confidences and evidence reliability into a desk-level score."""

    def combine(
        self,
        outputs: list[AgentOutput],
        evidence: list[EvidenceItem],
    ) -> ConfidenceBreakdown:
        if not outputs:
            return ConfidenceBreakdown(
                score=0,
                supports=[],
                challenges=["No agent outputs"],
                rationale="No analyst outputs were available, so confidence is zero.",
            )

        scores = [o.confidence.score for o in outputs]
        avg = sum(scores) / len(scores)
        reliability = (
            sum(item.reliability for item in evidence) / len(evidence) if evidence else 0.4
        )
        blended = int(max(0, min(100, round(avg * 0.7 + reliability * 100 * 0.3))))

        supports: list[str] = []
        challenges: list[str] = []
        for output in outputs:
            supports.extend(output.confidence.supports[:2])
            challenges.extend(output.confidence.challenges[:2])

        # Penalize disagreement across agents
        spread = max(scores) - min(scores)
        if spread >= 25:
            blended = max(0, blended - 8)
            challenges.append(f"Analyst disagreement spread={spread}")

        return ConfidenceBreakdown(
            score=blended,
            supports=list(dict.fromkeys(supports))[:8],
            challenges=list(dict.fromkeys(challenges))[:8],
            rationale=(
                f"Desk confidence is {blended}% because analyst scores averaged {avg:.0f} "
                f"with mean evidence reliability {reliability:.2f}"
                + (f" and material disagreement (spread {spread})." if spread >= 25 else ".")
            ),
        )
