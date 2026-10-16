"""Step 2 — Materiality Engine: score every change; ignore noise."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ile.comparator import ComparisonResult, FieldChange
from app.ile.policy import MaterialityScore, MaterialityTier, score_event_change, score_numeric_change


@dataclass
class ScoredChange:
    change: FieldChange
    materiality: MaterialityScore


@dataclass
class MaterialityResult:
    scored: list[ScoredChange] = field(default_factory=list)
    learnable: list[ScoredChange] = field(default_factory=list)
    ignored: list[ScoredChange] = field(default_factory=list)


class MaterialityEngine:
    def evaluate(self, comparison: ComparisonResult) -> MaterialityResult:
        result = MaterialityResult()
        for change in comparison.changes:
            if change.kind == "numeric":
                mat = score_numeric_change(
                    change.field_name,
                    previous=change.previous_value,
                    new=change.new_value,
                )
            else:
                mat = score_event_change(
                    change.field_name,
                    text=str(change.new_value),
                )
            scored = ScoredChange(change=change, materiality=mat)
            result.scored.append(scored)
            if mat.learn and mat.tier != MaterialityTier.IGNORE:
                result.learnable.append(scored)
            else:
                result.ignored.append(scored)
        return result
