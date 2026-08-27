"""Step 9 — Learning Timeline: company evolution over time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.contracts.models import KnowledgeObject, new_id, utc_now
from app.ile.materiality import ScoredChange


@dataclass
class TimelineEntry:
    entry_id: str
    company_symbol: str
    year: int
    label: str
    detail: str
    field_name: str
    importance: str
    object_id: str | None
    created_at: str


class LearningTimelineWriter:
    def write(
        self,
        ko: KnowledgeObject,
        learnable: list[ScoredChange],
    ) -> list[TimelineEntry]:
        if not ko.company_symbol or not learnable:
            return []
        year = datetime.now(timezone.utc).year
        out: list[TimelineEntry] = []
        for scored in learnable:
            label = _label(scored)
            out.append(
                TimelineEntry(
                    entry_id=new_id(),
                    company_symbol=ko.company_symbol,
                    year=year,
                    label=label,
                    detail=_detail(scored),
                    field_name=scored.change.field_name,
                    importance=scored.materiality.importance,
                    object_id=ko.object_id,
                    created_at=utc_now().isoformat(),
                )
            )
        return out


def _label(scored: ScoredChange) -> str:
    field = scored.change.field_name
    try:
        up = float(scored.change.new_value) > float(scored.change.previous_value)
    except (TypeError, ValueError):
        up = True
    mapping = {
        "revenue_growth": "Revenue Acceleration" if up else "Revenue Slowdown",
        "earnings_growth": "Earnings Acceleration" if up else "Earnings Slowdown",
        "pat_margin": "Margin Expansion" if up else "Margin Compression",
        "ebitda_margin": "Margin Expansion" if up else "Margin Compression",
        "debt": "Deleveraging" if not up else "Leverage Increase",
        "cash": "Cash Strengthening" if up else "Cash Weakening",
        "pe": "Valuation Re-rating" if up else "Valuation De-rating",
        "pe_ratio": "Valuation Re-rating" if up else "Valuation De-rating",
        "action_type": "Corporate Action",
        "object_created": "New Corporate Event",
        "guidance": "Guidance Change",
    }
    return mapping.get(field, field.replace("_", " ").title())


def _detail(scored: ScoredChange) -> str:
    return (
        f"{scored.change.field_name}: {scored.change.previous_value} → {scored.change.new_value} "
        f"(score {scored.materiality.score})"
    )
