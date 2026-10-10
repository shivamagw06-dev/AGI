"""Step 14 — Learning loop (in-memory V1; improves future retrieval cues)."""

from __future__ import annotations

from typing import Any

from app.irp.models import IrpPackage, LearningRecord


class IrpLearningStore:
    """Process-local learning memory — no KIP schema redesign in V1."""

    def __init__(self) -> None:
        self._records: list[LearningRecord] = []

    def record(self, package: IrpPackage, *, quality_score: float | None = None) -> LearningRecord:
        used = [r.document_id or r.title for r in package.ranked_evidence if r.document_id or r.title]
        rejected = [
            f"{r.document_id or r.title}:{r.reject_reason}"
            for r in package.rejected_evidence
            if r.document_id or r.title
        ]
        q = quality_score
        if q is None:
            q = _quality(package)
        rec = LearningRecord(
            question=package.question,
            intent=package.intent,
            domain=package.domain,
            entities=package.entities.model_dump(mode="json"),
            research_plan=package.research_plan.model_dump(mode="json") if package.research_plan else {},
            evidence_used=[str(x) for x in used][:40],
            rejected_evidence=[str(x) for x in rejected][:40],
            final_reasoning=package.reasoning.model_dump(mode="json"),
            follow_ups=list(package.follow_ups)[:8],
            quality_score=round(float(q), 4),
        )
        self._records.append(rec)
        # Cap memory
        if len(self._records) > 500:
            self._records = self._records[-500:]
        return rec

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return [r.model_dump(mode="json") for r in self._records[-limit:]]

    def cues_for(self, question: str) -> dict[str, Any]:
        """Return lightweight retrieval cues from prior similar questions."""
        ql = (question or "").lower()
        hits = [r for r in reversed(self._records) if _overlap(ql, r.question.lower()) >= 0.25][:5]
        reject: list[str] = []
        prefer: list[str] = []
        for h in hits:
            reject.extend(h.rejected_evidence[:5])
            prefer.extend(h.evidence_used[:5])
        return {
            "similar_questions": [h.question for h in hits],
            "prefer_evidence": prefer[:12],
            "avoid_evidence": reject[:12],
        }


def _quality(package: IrpPackage) -> float:
    score = 0.35
    if package.validation.passed:
        score += 0.25
    if package.ranked_evidence:
        score += 0.15
    if package.reasoning.bear_case or package.reasoning.bull_case:
        score += 0.1
    if package.reasoning.key_drivers:
        score += 0.1
    if package.follow_ups:
        score += 0.05
    return min(0.98, score)


def _overlap(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
