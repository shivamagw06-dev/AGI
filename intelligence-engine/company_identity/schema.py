"""Canonical company identity contract.

Capital IQ is the single source of truth for company identity and
classification. Nothing downstream may infer or override these fields.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

CIS_VERSION = "cis-v1.0"

# The only Primary Sector labels that may ever be emitted (CapIQ / GICS).
PRIMARY_SECTORS: tuple[str, ...] = (
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
)

SOURCE_CAPIQ_CONSENSUS = "capiq_valuation_consensus"
SOURCE_CAPIQ_IKT = "capiq_institutional_knowledge_tables"
SOURCE_NONE = "unresolved"


@dataclass
class CompanyIdentity:
    """Immutable canonical identity consumed by every engine."""

    ticker: str
    company_name: str
    primary_sector: Optional[str]
    primary_industry: Optional[str]
    business_type: Optional[str]
    industry_dna: Optional[str]
    industry_classification: Optional[str] = None
    exchange: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    parent: Optional[str] = None
    products: Optional[str] = None
    competitors: Optional[str] = None
    business_description: Optional[str] = None
    market_cap: Optional[str] = None
    enterprise_value: Optional[str] = None
    company_type: Optional[str] = None
    currency: Optional[str] = None
    trading_status: Optional[str] = None
    isin: Optional[str] = None
    allowed_valuation: tuple[str, ...] = ()
    forbidden_valuation: tuple[str, ...] = ()
    kpis: tuple[str, ...] = ()
    forbidden_kpis: tuple[str, ...] = ()
    source: str = SOURCE_NONE
    resolved: bool = False
    version: str = CIS_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("allowed_valuation", "forbidden_valuation", "kpis", "forbidden_kpis"):
            d[k] = list(getattr(self, k) or ())
        return d

    def context(self) -> dict[str, Any]:
        """Compact immutable context every downstream engine consumes."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "primary_sector": self.primary_sector,
            "primary_industry": self.primary_industry,
            "business_type": self.business_type,
            "industry_dna": self.industry_dna,
        }


@dataclass
class ClassificationViolation:
    rule: str
    detail: str
    severity: str = "fail"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    ok: bool
    ticker: Optional[str]
    violations: list[ClassificationViolation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "ticker": self.ticker,
            "violations": [v.to_dict() for v in self.violations],
        }
