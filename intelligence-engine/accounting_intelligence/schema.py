"""Accounting Intelligence Engine (ACI) V1 — schemas.

Primary question: Can the financial statements be trusted?
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

ACI_VERSION = "accounting-intelligence-engine-v1.0.0"

EARNINGS_QUALITY_LABELS = ("High", "Medium", "Low", "Questionable")
ACCRUAL_LABELS = ("Healthy", "Watch", "Aggressive")
THESIS_IMPACT = (
    "strengthens_thesis",
    "neutral",
    "weakens_thesis",
    "critical_review_required",
)

# Accounting Behaviour Engine (V1 fingerprint — evolves with evidence)
BEHAVIOUR_ARCHETYPES = (
    "Conservative",
    "Neutral",
    "Aggressive",
    "Improving",
    "Deteriorating",
    "Highly Predictable",
    "Earnings Management Risk",
    "Conservative and Consistent",
    "Increasingly Aggressive",
)


@dataclass
class AccountingObservation:
    obs_id: str
    ticker: str
    period: str
    as_of: str
    domain: str  # earnings|cash|accruals|revenue|wc|balance_sheet|policy|forensic
    claim: str
    evidence_doc: str = ""
    evidence_tier: int = 2
    metric: str = ""
    value: float | None = None
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyChange:
    change_id: str
    ticker: str
    period: str
    as_of: str
    policy: str
    description: str
    materiality: str  # material|non_material
    evidence_doc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForensicInputs:
    """Inputs for Beneish / Piotroski / Altman style models (evidence-backed)."""

    # Beneish components (indexes ≈ 1.0 = neutral)
    dsri: float = 1.0
    gmi: float = 1.0
    aqi: float = 1.0
    sgi: float = 1.0
    depi: float = 1.0
    sgai: float = 1.0
    lvgi: float = 1.0
    tata: float = 0.0
    # Piotroski binary signals (0/1)
    f_roa_pos: int = 1
    f_cfo_pos: int = 1
    f_roa_up: int = 1
    f_accrual_ok: int = 1  # CFO > NI
    f_leverage_down: int = 1
    f_current_up: int = 1
    f_no_dilution: int = 1
    f_gross_margin_up: int = 1
    f_asset_turnover_up: int = 1
    # Altman Z (simplified manufacturing / non-bank)
    z_wc_ta: float = 0.2
    z_re_ta: float = 0.3
    z_ebit_ta: float = 0.15
    z_me_tl: float = 2.0
    z_sales_ta: float = 0.8
    bank_mode: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
