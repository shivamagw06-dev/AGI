"""In-memory versioned history for InstitutionalPortfolioDecision."""

from __future__ import annotations

from typing import Any, Optional

from institutional_portfolio_decision.models import InstitutionalPortfolioDecision

_HISTORY: dict[str, list[InstitutionalPortfolioDecision]] = {}


def reset_for_tests() -> None:
    _HISTORY.clear()


def record(decision: InstitutionalPortfolioDecision) -> None:
    key = decision.portfolio_id
    _HISTORY.setdefault(key, []).append(decision)
    if len(_HISTORY[key]) > 100:
        _HISTORY[key] = _HISTORY[key][-100:]


def latest(portfolio_id: str) -> Optional[InstitutionalPortfolioDecision]:
    rows = _HISTORY.get(str(portfolio_id) or "", [])
    return rows[-1] if rows else None


def list_versions(portfolio_id: str) -> list[dict[str, Any]]:
    rows = _HISTORY.get(str(portfolio_id) or "", [])
    return [
        {
            "decision_id": d.decision_id,
            "decision_version": d.decision_version,
            "recommendation": d.recommendation,
            "confidence": d.confidence,
            "generated_at": d.generated_at,
        }
        for d in rows
    ]


def metrics() -> dict[str, Any]:
    return {
        "portfolios": sorted(_HISTORY.keys()),
        "decision_count": sum(len(v) for v in _HISTORY.values()),
    }
