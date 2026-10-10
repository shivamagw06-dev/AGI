"""Immutable knowledge contracts for financial-sector valuation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

FINANCIALS_VALUATION_VERSION = "financials-valuation-v1.0.0"
SUBSECTORS = ("COMMERCIAL_BANK", "SMALL_FINANCE_BANK", "PAYMENTS_BANK", "NBFC", "HOUSING_FINANCE",
              "LIFE_INSURANCE", "GENERAL_INSURANCE", "HEALTH_INSURANCE", "ASSET_MANAGEMENT",
              "BROKER", "EXCHANGE_INFRASTRUCTURE", "FINTECH_PAYMENTS", "DIVERSIFIED_FINANCIALS")

@dataclass(frozen=True)
class KPIKnowledge:
    key: str; name: str; definition: str; formula: str; unit: str; frequency: str
    preferred_sources: tuple[str, ...]; why_it_matters: str; causal_relationships: tuple[str, ...]
    valuation_relationship: str; limitations: str; acceptable_quality: tuple[str, ...]

@dataclass(frozen=True)
class ValuationMethodRule:
    method: str; tier: str; reason_for_use: str; required_inputs: tuple[str, ...]
    strengths: tuple[str, ...]; weaknesses: tuple[str, ...]; failure_conditions: tuple[str, ...]

@dataclass(frozen=True)
class SectorValuationModel:
    sector_id: str; sector_name: str; subsector: str; business_model_types: tuple[str, ...]
    economic_structure: str; revenue_drivers: tuple[str, ...]; cost_drivers: tuple[str, ...]
    capital_structure: str; regulatory_characteristics: tuple[str, ...]; key_kpis: tuple[KPIKnowledge, ...]
    valuation_methods: tuple[ValuationMethodRule, ...]; valuation_drivers: tuple[str, ...]
    valuation_risks: tuple[str, ...]; scenario_variables: tuple[str, ...]; monitoring_variables: tuple[str, ...]
    common_analytical_errors: tuple[str, ...]; evidence_sources: tuple[str, ...]
    effective_date: str; confidence: float; validation_status: str = "VALIDATED"
    version: str = FINANCIALS_VALUATION_VERSION
    def to_dict(self) -> dict[str, Any]: return asdict(self)
