"""Portfolio graph entities and the InstitutionalPortfolio object."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence


def _nid(portfolio_id: str, kind: str, key: str) -> str:
    raw = f"{portfolio_id}|{kind}|{key}".lower().replace(" ", "_")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return f"pkg:{portfolio_id.lower()}:{kind}:{digest}"


@dataclass(frozen=True)
class PortfolioEntity:
    id: str
    type: str
    label: str
    version: str = "1"
    timestamp: str = ""
    source: str = "institutional_portfolio"
    confidence: float = 0.8
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "version": self.version,
            "timestamp": self.timestamp,
            "source": self.source,
            "confidence": float(self.confidence),
            "attributes": dict(self.attributes or {}),
        }


@dataclass(frozen=True)
class PortfolioRelationship:
    id: str
    source_id: str
    target_id: str
    kind: str
    label: str = ""
    strength: float = 0.5
    weight: float = 0.0
    confidence: float = 0.8
    inferred: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "kind": self.kind,
            "label": self.label or self.kind,
            "strength": float(self.strength),
            "weight": float(self.weight),
            "confidence": float(self.confidence),
            "inferred": bool(self.inferred),
            "attributes": dict(self.attributes or {}),
        }


@dataclass(frozen=True)
class HoldingRecord:
    ticker: str
    company: str
    weight: float
    market_value: float = 0.0
    quantity: float = 0.0
    sector: str = ""
    industry: str = ""
    country: str = "IN"
    recommendation: str = ""
    confidence: int = 0
    decision_id: str = ""
    company_graph_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company": self.company,
            "weight": float(self.weight),
            "market_value": float(self.market_value),
            "quantity": float(self.quantity),
            "sector": self.sector,
            "industry": self.industry,
            "country": self.country,
            "recommendation": self.recommendation,
            "confidence": int(self.confidence),
            "decision_id": self.decision_id,
            "company_graph_id": self.company_graph_id,
        }


@dataclass(frozen=True)
class AllocationRecord:
    ticker: str
    weight: float
    target_band: str = ""
    role: str = "core"

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "weight": float(self.weight),
            "target_band": self.target_band,
            "role": self.role,
        }


@dataclass(frozen=True)
class ExposureRecord:
    dimension: str  # sector | country | industry | recommendation
    name: str
    weight: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "name": self.name,
            "weight": float(self.weight),
        }


@dataclass(frozen=True)
class RiskRecord:
    kind: str
    label: str
    severity: str
    score: float
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "severity": self.severity,
            "score": float(self.score),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DecisionSummary:
    ticker: str
    recommendation: str
    confidence: int
    decision_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "recommendation": self.recommendation,
            "confidence": int(self.confidence),
            "decision_id": self.decision_id,
        }


@dataclass(frozen=True)
class InstitutionalPortfolio:
    """First-class portfolio intelligence object for the Investment Office."""

    portfolio_id: str
    name: str
    holdings: tuple[HoldingRecord, ...] = ()
    allocations: tuple[AllocationRecord, ...] = ()
    exposures: tuple[ExposureRecord, ...] = ()
    risks: tuple[RiskRecord, ...] = ()
    decisions: tuple[DecisionSummary, ...] = ()
    cash_weight: float = 0.0
    base_currency: str = "INR"
    graph_id: str = ""
    version: str = ""
    as_of: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "holdings": [h.to_dict() for h in self.holdings],
            "allocations": [a.to_dict() for a in self.allocations],
            "exposures": [e.to_dict() for e in self.exposures],
            "risks": [r.to_dict() for r in self.risks],
            "decisions": [d.to_dict() for d in self.decisions],
            "cash_weight": float(self.cash_weight),
            "base_currency": self.base_currency,
            "graph_id": self.graph_id,
            "version": self.version,
            "as_of": self.as_of,
            "holding_count": len(self.holdings),
            "llm": False,
        }


def make_entity(
    portfolio_id: str,
    type_: str,
    key: str,
    label: str,
    *,
    confidence: float = 0.8,
    timestamp: str = "",
    attributes: Optional[dict[str, Any]] = None,
) -> PortfolioEntity:
    return PortfolioEntity(
        id=_nid(portfolio_id, type_, key),
        type=type_,
        label=label,
        timestamp=timestamp,
        confidence=confidence,
        attributes=dict(attributes or {}),
    )


def make_relationship(
    portfolio_id: str,
    source_id: str,
    target_id: str,
    kind: str,
    *,
    label: str = "",
    strength: float = 0.5,
    weight: float = 0.0,
    confidence: float = 0.8,
    inferred: bool = False,
    attributes: Optional[dict[str, Any]] = None,
) -> PortfolioRelationship:
    rid = _nid(portfolio_id, "rel", f"{kind}|{source_id}|{target_id}")
    return PortfolioRelationship(
        id=rid,
        source_id=source_id,
        target_id=target_id,
        kind=kind,
        label=label or kind,
        strength=strength,
        weight=weight,
        confidence=confidence,
        inferred=inferred,
        attributes=dict(attributes or {}),
    )
