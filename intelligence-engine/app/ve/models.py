"""VE domain models — versioned valuation objects; never overwrite."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class Assumption:
    name: str
    value: float
    source: str = "default"
    confidence: float = 0.5
    timestamp: str = field(default_factory=_now)
    version: int = 1
    unit: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioCase:
    name: str  # bull | base | bear
    intrinsic_value: float
    probability: float
    confidence: float
    assumptions: list[Assumption] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "intrinsic_value": self.intrinsic_value,
            "probability": self.probability,
            "confidence": self.confidence,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "notes": self.notes,
        }


@dataclass
class MarginOfSafety:
    market_price: float
    intrinsic_value: float
    discount_premium_pct: float
    suggested_mos_pct: float
    historical_percentile: float
    undervalued: bool
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelResult:
    model: str
    intrinsic_value: float
    fair_value: float
    equity_value: float | None = None
    enterprise_value: float | None = None
    multiple: float | None = None
    confidence: float = 0.5
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SensitivityPoint:
    parameter: str
    delta_pct: float
    intrinsic_value: float
    change_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PeerRow:
    symbol: str
    pe: float = 0.0
    ev_ebitda: float = 0.0
    ev_sales: float = 0.0
    pb: float = 0.0
    roce: float = 0.0
    roe: float = 0.0
    growth: float = 0.0
    margin: float = 0.0
    leverage: float = 0.0
    fcf_yield: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValuationObject:
    valuation_id: str
    company_id: str
    company_symbol: str
    fiscal_year: str
    version: int
    models: list[ModelResult] = field(default_factory=list)
    primary_model: str = "dcf_fcff"
    intrinsic_value: float = 0.0
    fair_value: float = 0.0
    market_price: float = 0.0
    blended_value: float = 0.0
    assumptions: list[Assumption] = field(default_factory=list)
    scenarios: list[ScenarioCase] = field(default_factory=list)
    margin_of_safety: MarginOfSafety | None = None
    sensitivity: list[SensitivityPoint] = field(default_factory=list)
    peers: list[PeerRow] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    forecast_ids: list[str] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    explainability: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    parent_valuation_id: str = ""
    superseded: bool = False
    soft_deleted: bool = False
    created_at: str = field(default_factory=_now)
    trigger: str = "manual"  # manual | auto | bus_event | ask_agi
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valuation_id": self.valuation_id,
            "company_id": self.company_id,
            "company_symbol": self.company_symbol,
            "fiscal_year": self.fiscal_year,
            "version": self.version,
            "models": [m.to_dict() for m in self.models],
            "primary_model": self.primary_model,
            "intrinsic_value": self.intrinsic_value,
            "fair_value": self.fair_value,
            "market_price": self.market_price,
            "blended_value": self.blended_value,
            "assumptions": [a.to_dict() for a in self.assumptions],
            "scenarios": [s.to_dict() for s in self.scenarios],
            "margin_of_safety": self.margin_of_safety.to_dict() if self.margin_of_safety else {},
            "sensitivity": [s.to_dict() for s in self.sensitivity],
            "peers": [p.to_dict() for p in self.peers],
            "evidence_ids": list(self.evidence_ids),
            "forecast_ids": list(self.forecast_ids),
            "event_ids": list(self.event_ids),
            "risks": list(self.risks),
            "explainability": dict(self.explainability),
            "confidence": self.confidence,
            "parent_valuation_id": self.parent_valuation_id,
            "superseded": self.superseded,
            "soft_deleted": self.soft_deleted,
            "created_at": self.created_at,
            "trigger": self.trigger,
            "metadata": dict(self.metadata),
        }
