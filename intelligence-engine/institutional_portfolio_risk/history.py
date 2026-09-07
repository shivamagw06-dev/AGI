"""In-memory versioned history for InstitutionalPortfolioRisk."""

from __future__ import annotations

from typing import Any, Optional

from institutional_portfolio_risk.models import InstitutionalPortfolioRisk

_HISTORY: dict[str, list[InstitutionalPortfolioRisk]] = {}


def reset_for_tests() -> None:
    _HISTORY.clear()


def record(risk: InstitutionalPortfolioRisk) -> None:
    key = risk.portfolio_id
    _HISTORY.setdefault(key, []).append(risk)
    if len(_HISTORY[key]) > 100:
        _HISTORY[key] = _HISTORY[key][-100:]


def latest(portfolio_id: str) -> Optional[InstitutionalPortfolioRisk]:
    rows = _HISTORY.get(str(portfolio_id) or "", [])
    return rows[-1] if rows else None


def list_versions(portfolio_id: str) -> list[dict[str, Any]]:
    rows = _HISTORY.get(str(portfolio_id) or "", [])
    return [
        {
            "risk_id": r.risk_id,
            "risk_version": r.risk_version,
            "overall_risk": r.overall_risk,
            "generated_at": r.generated_at,
        }
        for r in rows
    ]


def metrics() -> dict[str, Any]:
    return {
        "portfolios": sorted(_HISTORY.keys()),
        "risk_count": sum(len(v) for v in _HISTORY.values()),
    }
