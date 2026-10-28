"""Filing Diff Engine (FDI) V1 — schemas.

Primary question: What materially changed since the previous filing?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

FDI_VERSION = "filing-diff-engine-v1.0.0"

MATERIALITY = ("critical", "high", "medium", "low", "ignore")
THESIS_IMPACT = (
    "strengthens_thesis",
    "neutral",
    "weakens_thesis",
    "unknown",
    "needs_committee_review",
)
GUIDANCE_MOVES = ("raised", "maintained", "lowered", "withdrawn")
OPTIMISM = ("increased", "decreased", "neutral")


@dataclass
class ChangeRecord:
    change_id: str
    ticker: str
    domain: str  # statement|notes|guidance|management|risks|segment|accounting|capital|governance|ownership
    metric: str
    change_type: str
    previous_value: Any
    current_value: Any
    previous_period: str
    current_period: str
    previous_doc_id: str = ""
    current_doc_id: str = ""
    section: str = ""
    page: str | int | None = None
    evidence_tier: int = 2
    materiality: str = "medium"
    thesis_impact: str = "unknown"
    what_changed: str = ""
    why_changed: str = ""
    drivers: list[str] = field(default_factory=list)
    implications: list[str] = field(default_factory=list)
    confidence: float = 0.75
    cosmetic: bool = False
    open_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
