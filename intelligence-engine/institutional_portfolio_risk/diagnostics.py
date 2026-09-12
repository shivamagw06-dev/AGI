"""PRE-01 diagnostics payload."""

from __future__ import annotations

from typing import Any, Optional

from institutional_portfolio_risk.models import InstitutionalPortfolioRisk
from institutional_portfolio_risk.schema import (
    LINEAGE_CHAIN,
    PRE_VERSION,
    PRE_WORKSTREAM_ID,
    RISK_ENGINE_VERSION,
    VALIDATOR_VERSION,
)


def build_diagnostics(
    risk: InstitutionalPortfolioRisk,
    *,
    validation: Optional[dict[str, Any]] = None,
    latency_ms: float = 0.0,
    holding_count: int = 0,
) -> dict[str, Any]:
    worst = None
    if risk.stress_results:
        worst = min(risk.stress_results, key=lambda s: float(s.portfolio_impact_pct))
    return {
        "workstream_id": PRE_WORKSTREAM_ID,
        "version": PRE_VERSION,
        "risk_engine_version": RISK_ENGINE_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "risk_id": risk.risk_id,
        "risk_version": risk.risk_version,
        "portfolio_id": risk.portfolio_id,
        "overall_risk": risk.overall_risk,
        "holding_count": int(holding_count),
        "concentration_level": risk.concentration.level,
        "liquidity_level": risk.liquidity.level,
        "correlation_level": risk.correlations.level,
        "hhi": risk.concentration.hhi,
        "sector_concentration": risk.concentration.sector_concentration,
        "top_sector": risk.concentration.top_sector,
        "worst_stress": worst.to_dict() if worst else None,
        "warning_count": len(risk.warnings),
        "recommendation_count": len(risk.recommendations),
        "lineage": list(LINEAGE_CHAIN),
        "latency_ms": round(float(latency_ms), 2),
        "validation": validation or {},
        "llm": False,
        "monte_carlo": False,
        "var": False,
        "authoritative": True,
    }
