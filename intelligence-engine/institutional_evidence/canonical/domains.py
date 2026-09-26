"""Canonical domain models — every engine consumes these, never provider payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema import CANONICAL_DOMAIN_MODELS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class CanonicalCompany:
    entity_id: str
    ticker: str
    name: str
    sector: str = ""
    isin: str = ""
    bse_code: str = ""
    nse_symbol: str = ""
    aliases: List[str] = field(default_factory=list)
    schema: str = "CanonicalCompany.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalMarketData:
    entity_id: str
    ticker: str
    as_of: Optional[str] = None
    ltp: Optional[float] = None
    currency: str = "INR"
    ohlc: Dict[str, Any] = field(default_factory=dict)
    volume: Optional[float] = None
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalMarketData.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalCorporateActions:
    entity_id: str
    ticker: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalCorporateActions.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalShareholding:
    entity_id: str
    ticker: str
    periods: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalShareholding.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalManagementGuidance:
    entity_id: str
    ticker: str
    guidance_items: List[Dict[str, Any]] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalManagementGuidance.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalTranscript:
    entity_id: str
    ticker: str
    period: str = ""
    speakers: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalTranscript.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalNewsEvent:
    entity_id: str
    ticker: str
    headline: str = ""
    published_at: Optional[str] = None
    event_type: str = "news"
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalNewsEvent.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalMacroSeries:
    series_id: str
    name: str
    points: List[Dict[str, Any]] = field(default_factory=list)
    source: str = ""
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalMacroSeries.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalValuation:
    entity_id: str
    ticker: str
    multiples: Dict[str, Any] = field(default_factory=dict)
    dcf: Dict[str, Any] = field(default_factory=dict)
    as_of: Optional[str] = None
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalValuation.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CanonicalForecast:
    entity_id: str
    ticker: str
    horizon: str = "12m"
    scenarios: Dict[str, Any] = field(default_factory=dict)
    evidence_refs: List[str] = field(default_factory=list)
    schema: str = "CanonicalForecast.v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def list_canonical_models() -> List[str]:
    return list(CANONICAL_DOMAIN_MODELS)


def empty_domain_bundle(entity_id: str, ticker: str, name: str = "") -> Dict[str, Any]:
    """Scaffold all canonical domain models for an entity (provider-agnostic)."""
    t = ticker.upper()
    return {
        "ok": True,
        "entity_id": entity_id,
        "ticker": t,
        "built_at": _now(),
        "rule": "Every engine consumes these models instead of provider-specific payloads",
        "models": {
            "CanonicalCompany": CanonicalCompany(
                entity_id=entity_id, ticker=t, name=name or t, nse_symbol=t
            ).to_dict(),
            "CanonicalFinancialStatements": None,  # filled by canonical.statements
            "CanonicalMarketData": CanonicalMarketData(entity_id=entity_id, ticker=t).to_dict(),
            "CanonicalCorporateActions": CanonicalCorporateActions(
                entity_id=entity_id, ticker=t
            ).to_dict(),
            "CanonicalShareholding": CanonicalShareholding(entity_id=entity_id, ticker=t).to_dict(),
            "CanonicalManagementGuidance": CanonicalManagementGuidance(
                entity_id=entity_id, ticker=t
            ).to_dict(),
            "CanonicalTranscript": CanonicalTranscript(entity_id=entity_id, ticker=t).to_dict(),
            "CanonicalNewsEvent": [],
            "CanonicalMacroSeries": [],
            "CanonicalValuation": CanonicalValuation(entity_id=entity_id, ticker=t).to_dict(),
            "CanonicalForecast": CanonicalForecast(entity_id=entity_id, ticker=t).to_dict(),
        },
    }
