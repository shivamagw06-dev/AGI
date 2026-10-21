"""CIO-01 diagnostics."""

from __future__ import annotations

from typing import Any, Optional

from institutional_portfolio_decision.models import InstitutionalPortfolioDecision
from institutional_portfolio_decision.schema import CIO_VERSION, CIO_WORKSTREAM_ID


def build_diagnostics(
    decision: InstitutionalPortfolioDecision,
    *,
    validation: Optional[dict[str, Any]] = None,
    latency_ms: float = 0.0,
) -> dict[str, Any]:
    return {
        "workstream_id": CIO_WORKSTREAM_ID,
        "version": CIO_VERSION,
        "portfolio_id": decision.portfolio_id,
        "decision_id": decision.decision_id,
        "decision_version": decision.decision_version,
        "recommendation": decision.recommendation,
        "rule_path": decision.rule_path,
        "allocation_action_count": len(decision.allocation_actions),
        "exposure_action_count": len(decision.exposure_actions),
        "supporting_count": len(decision.supporting_decisions),
        "contradicting_count": len(decision.contradicting_decisions),
        "monitoring_item_count": len(decision.monitoring_items),
        "lineage": list(decision.lineage),
        "mutates_company_decisions": False,
        "validation": validation,
        "latency_ms": round(latency_ms, 4),
        "llm": False,
    }
