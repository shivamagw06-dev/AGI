"""SIF schema — sector framework knowledge objects (analysis lenses, not curriculum)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


SIF_VERSION = "sif-v1.0.0"


@dataclass
class SectorFramework:
    """Canonical institutional sector analysis checklist."""

    sector_id: str
    name: str
    version: str = SIF_VERSION
    aliases: list[str] = field(default_factory=list)
    business_model_focus: list[str] = field(default_factory=list)
    required_kpis: list[str] = field(default_factory=list)
    priority_metrics: list[str] = field(default_factory=list)
    accounting_focus: list[str] = field(default_factory=list)
    corporate_finance_focus: list[str] = field(default_factory=list)
    academy_concept_priority: list[str] = field(default_factory=list)
    valuation_methodology: list[str] = field(default_factory=list)
    preferred_multiples: list[str] = field(default_factory=list)
    forecast_drivers: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    industry_mental_models: list[str] = field(default_factory=list)
    decision_framework: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    monitoring_signals: list[str] = field(default_factory=list)
    iie_focus: list[str] = field(default_factory=list)
    evidence_required: list[str] = field(default_factory=list)
    suppress_generic_concepts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
