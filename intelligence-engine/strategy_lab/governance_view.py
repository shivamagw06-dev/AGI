"""Fail-closed governance metadata for product-facing strategy aliases."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any


PRODUCT_STRATEGY_ALIASES = MappingProxyType(
    {
        "value": "relative_value_v1",
        "quality": "quality_v1",
        "growth": "growth_v1",
        "momentum": "momentum_v1",
        "technical": "momentum_v1",
        "conviction": "consensus_revisions_v1",
        "dividend": "value_quality_v1",
        "stress": "stress_v1",
        "pairs": "pairs_v1",
        "live_alpha": "multi_factor_v1",
        "alpha": "multi_factor_v1",
        "cross_sectional_momentum_v1": "momentum_v1",
        "volume_liquidity_anomaly_v1": "volume_anomaly_v1",
        "opening_range_expansion_v1": "opening_range_v1",
        "opening_range_breakout": "opening_range_v1",
        "intraday_mean_reversion_v1": "mean_reversion_v1",
        "intraday_reversion": "mean_reversion_v1",
        "flow_anomaly": "volume_anomaly_v1",
        "derivatives_positioning_v1": "derivatives_positioning_v1",
        "agi_sector_rotation_v1": "sector_rotation_v1",
        "agi_equity_opportunity_v1": "multi_factor_v1",
    }
)

CANONICAL_ROLES = MappingProxyType(
    {
        "relative_value_v1": "relative_value_research",
        "quality_v1": "quality_factor_research",
        "value_quality_v1": "income_and_value_quality_research",
        "momentum_v1": "price_leadership_research",
        "sector_rotation_v1": "sector_allocation_research",
        "growth_v1": "growth_factor_research",
        "consensus_revisions_v1": "expectations_revision_research",
        "stress_v1": "downside_risk_research",
        "multi_factor_v1": "research_shortlist_overlay",
        "mean_reversion_v1": "intraday_dislocation_research",
        "opening_range_v1": "intraday_breakout_research",
        "volume_anomaly_v1": "liquidity_and_flow_research",
        "pairs_v1": "relative_value_pair_research",
        "derivatives_positioning_v1": "derivatives_positioning_research",
    }
)


def canonical_strategy_id(product_strategy_id: str) -> str:
    key = str(product_strategy_id or "").strip()
    return PRODUCT_STRATEGY_ALIASES.get(key, key)


def governance_for(product_strategy_id: str) -> dict[str, Any]:
    """Map a product id without manufacturing evidence or capital permission."""
    product_id = str(product_strategy_id or "").strip()
    canonical_id = canonical_strategy_id(product_id)
    mapped = canonical_id in CANONICAL_ROLES
    return {
        "product_strategy_id": product_id,
        "canonical_strategy_id": canonical_id,
        "is_alias": product_id != canonical_id,
        "mapped": mapped,
        "role": CANONICAL_ROLES.get(canonical_id, "unmapped_research"),
        "stage": "DEFINED" if mapped else "UNMAPPED",
        "declared_status": "RESEARCH_ONLY",
        "evidence_status": "PROSPECTIVE_VALIDATION_PENDING" if mapped else "MAPPING_REQUIRED",
        "capital_allowed": False,
        "alpha_claims_permitted": False,
    }


def migration_manifest() -> tuple[dict[str, Any], ...]:
    return tuple(governance_for(product_id) for product_id in sorted(PRODUCT_STRATEGY_ALIASES))
