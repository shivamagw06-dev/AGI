"""In-memory versioned history for InstitutionalCommitteeResolution."""

from __future__ import annotations

from typing import Any, Optional

from institutional_committee.models import InstitutionalCommitteeResolution

_BY_ID: dict[str, InstitutionalCommitteeResolution] = {}
_BY_PORTFOLIO: dict[str, list[InstitutionalCommitteeResolution]] = {}
_PENDING: list[str] = []


def reset_for_tests() -> None:
    _BY_ID.clear()
    _BY_PORTFOLIO.clear()
    _PENDING.clear()


def record(resolution: InstitutionalCommitteeResolution) -> None:
    _BY_ID[resolution.resolution_id] = resolution
    key = resolution.portfolio_id
    _BY_PORTFOLIO.setdefault(key, []).append(resolution)
    if len(_BY_PORTFOLIO[key]) > 100:
        _BY_PORTFOLIO[key] = _BY_PORTFOLIO[key][-100:]
    if resolution.status == "Pending Review":
        if resolution.resolution_id not in _PENDING:
            _PENDING.append(resolution.resolution_id)
    elif resolution.resolution_id in _PENDING:
        _PENDING.remove(resolution.resolution_id)


def get(resolution_id: str) -> Optional[InstitutionalCommitteeResolution]:
    return _BY_ID.get(str(resolution_id) or "")


def latest(portfolio_id: str) -> Optional[InstitutionalCommitteeResolution]:
    rows = _BY_PORTFOLIO.get(str(portfolio_id) or "", [])
    return rows[-1] if rows else None


def pending() -> list[InstitutionalCommitteeResolution]:
    out: list[InstitutionalCommitteeResolution] = []
    for rid in list(_PENDING):
        r = _BY_ID.get(rid)
        if r and r.status == "Pending Review":
            out.append(r)
        elif rid in _PENDING:
            _PENDING.remove(rid)
    return out


def list_for_portfolio(portfolio_id: str) -> list[dict[str, Any]]:
    rows = _BY_PORTFOLIO.get(str(portfolio_id) or "", [])
    return [
        {
            "resolution_id": r.resolution_id,
            "resolution_version": r.resolution_version,
            "status": r.status,
            "outcome": r.outcome,
            "portfolio_decision_id": r.portfolio_decision_id,
            "generated_at": r.generated_at,
        }
        for r in rows
    ]


def all_resolutions() -> list[InstitutionalCommitteeResolution]:
    return list(_BY_ID.values())


def metrics() -> dict[str, Any]:
    rows = list(_BY_ID.values())
    by_status: dict[str, int] = {}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    return {
        "portfolios": sorted(_BY_PORTFOLIO.keys()),
        "resolution_count": len(rows),
        "pending_count": len(pending()),
        "by_status": by_status,
    }
