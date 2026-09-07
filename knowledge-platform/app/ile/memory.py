"""Step 8 — Institutional Memory: reusable narrative knowledge, not raw metrics."""

from __future__ import annotations

from dataclasses import dataclass

from app.contracts.models import KnowledgeObject, new_id, utc_now
from app.ile.impact import ImpactAssessment
from app.ile.materiality import ScoredChange


@dataclass
class MemoryEntry:
    memory_id: str
    company_symbol: str
    narrative: str
    category: str
    importance: str
    source_learning_fields: list[str]
    object_id: str | None
    created_at: str


class InstitutionalMemoryWriter:
    def write(
        self,
        ko: KnowledgeObject,
        learnable: list[ScoredChange],
        impact: ImpactAssessment,
    ) -> list[MemoryEntry]:
        if not ko.company_symbol or not learnable:
            return []
        company = (
            (ko.knowledge or {}).get("company")
            or ko.entity_refs.company_name
            or ko.company_symbol
        )
        narratives = _compose_narratives(company, learnable)
        out: list[MemoryEntry] = []
        for category, narrative, importance, fields in narratives:
            out.append(
                MemoryEntry(
                    memory_id=new_id(),
                    company_symbol=ko.company_symbol,
                    narrative=narrative,
                    category=category,
                    importance=importance,
                    source_learning_fields=fields,
                    object_id=ko.object_id,
                    created_at=utc_now().isoformat(),
                )
            )
        return out


def _compose_narratives(company: str, learnable: list[ScoredChange]):
    fields = {s.change.field_name: s for s in learnable}
    results = []

    rev = fields.get("revenue_growth")
    margin = fields.get("pat_margin") or fields.get("ebitda_margin")
    cash = fields.get("cash")
    debt = fields.get("debt")

    if rev and _up(rev):
        bits = [
            f"{company} has entered a stronger growth phase"
        ]
        if margin and _up(margin):
            bits.append("driven by improved execution and operating leverage")
        elif debt and not _up(debt):
            bits.append("with a healthier balance sheet supporting expansion")
        else:
            bits.append("driven by improved demand and execution")
        narrative = " ".join(bits) + "."
        used = ["revenue_growth"]
        if margin:
            used.append(margin.change.field_name)
        results.append(("Financial Performance", narrative, rev.materiality.importance, used))
    elif rev and not _up(rev):
        results.append(
            (
                "Financial Performance",
                f"{company} growth momentum has moderated versus the prior trend.",
                rev.materiality.importance,
                ["revenue_growth"],
            )
        )

    if margin and _up(margin) and not rev:
        results.append(
            (
                "Financial Performance",
                f"{company} margins are expanding, indicating improving operating efficiency.",
                margin.materiality.importance,
                [margin.change.field_name],
            )
        )
    if margin and not _up(margin):
        results.append(
            (
                "Financial Performance",
                f"{company} is experiencing margin pressure that may reflect sector-wide cost dynamics.",
                margin.materiality.importance,
                [margin.change.field_name],
            )
        )

    if cash and _up(cash):
        results.append(
            (
                "Financial Performance",
                f"{company} cash generation has strengthened.",
                cash.materiality.importance,
                ["cash"],
            )
        )
    if debt and not _up(debt):
        results.append(
            (
                "Financial Performance",
                f"{company} has reduced leverage, strengthening balance-sheet flexibility.",
                debt.materiality.importance,
                ["debt"],
            )
        )

    pe = fields.get("pe") or fields.get("pe_ratio")
    if pe:
        direction = "re-rating higher" if _up(pe) else "de-rating"
        results.append(
            (
                "Valuation",
                f"{company} valuation is {direction} on updated fundamentals.",
                pe.materiality.importance,
                [pe.change.field_name],
            )
        )

    if not results:
        # Generic fallback for other material learnings
        top = max(learnable, key=lambda s: s.materiality.score)
        results.append(
            (
                top.materiality.category,
                f"{company} registered a material change in {top.change.field_name.replace('_', ' ')}.",
                top.materiality.importance,
                [top.change.field_name],
            )
        )
    return results


def _up(scored: ScoredChange) -> bool:
    try:
        return float(scored.change.new_value) > float(scored.change.previous_value)
    except (TypeError, ValueError):
        return False
