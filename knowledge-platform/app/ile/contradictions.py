"""Step 7 — Contradiction Engine: detect invalidated prior assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.contracts.models import KnowledgeObject, new_id
from app.ile.materiality import ScoredChange


@dataclass
class KnowledgeConflict:
    conflict_id: str
    company_symbol: str | None
    status: str  # Needs Review
    reason: str
    previous_assumption: str
    new_observation: str
    field_name: str
    previous_value: Any
    new_value: Any
    object_id: str | None = None


class ContradictionEngine:
    """Flag only when a previously constructive narrative is invalidated."""

    def detect(
        self,
        ko: KnowledgeObject,
        learnable: list[ScoredChange],
    ) -> list[KnowledgeConflict]:
        conflicts: list[KnowledgeConflict] = []
        for scored in learnable:
            field = scored.change.field_name
            try:
                prev = float(scored.change.previous_value)
                new = float(scored.change.new_value)
            except (TypeError, ValueError):
                continue

            if field in {"revenue_growth", "earnings_growth", "pat_margin", "ebitda_margin", "cash"}:
                if new < prev:
                    conflicts.append(
                        KnowledgeConflict(
                            conflict_id=new_id(),
                            company_symbol=ko.company_symbol,
                            status="Needs Review",
                            reason="Previous assumption invalidated.",
                            previous_assumption=_positive_assumption(field),
                            new_observation=_negative_observation(field),
                            field_name=field,
                            previous_value=prev,
                            new_value=new,
                            object_id=ko.object_id,
                        )
                    )
            elif field == "debt" and new > prev:
                conflicts.append(
                    KnowledgeConflict(
                        conflict_id=new_id(),
                        company_symbol=ko.company_symbol,
                        status="Needs Review",
                        reason="Previous assumption invalidated.",
                        previous_assumption="Deleveraging / balance sheet improving",
                        new_observation="Leverage rising",
                        field_name=field,
                        previous_value=prev,
                        new_value=new,
                        object_id=ko.object_id,
                    )
                )
        return conflicts


def _positive_assumption(field: str) -> str:
    return {
        "revenue_growth": "Margins expanding / growth durable",
        "earnings_growth": "Earnings momentum intact",
        "pat_margin": "Margins expanding",
        "ebitda_margin": "Margins expanding",
        "cash": "Cash generation strengthening",
    }.get(field, "Prior constructive thesis")


def _negative_observation(field: str) -> str:
    return {
        "revenue_growth": "Growth decelerating",
        "earnings_growth": "Earnings momentum fading",
        "pat_margin": "Margins declining",
        "ebitda_margin": "Margins declining",
        "cash": "Cash position weakening",
    }.get(field, "Thesis under pressure")
