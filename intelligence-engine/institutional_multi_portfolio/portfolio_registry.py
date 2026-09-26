"""MPC-01 Portfolio Registry — first-class portfolios referencing shared intelligence."""

from __future__ import annotations

from typing import Any, Optional

from institutional_multi_portfolio.mandate_engine import resolve_mandate
from institutional_multi_portfolio.models import InstitutionalPortfolioRecord
from institutional_multi_portfolio.schema import SEED_PORTFOLIOS

_PORTFOLIOS: dict[str, InstitutionalPortfolioRecord] = {}


def reset_for_tests() -> None:
    _PORTFOLIOS.clear()
    bootstrap_seed_portfolios()


def bootstrap_seed_portfolios() -> None:
    if _PORTFOLIOS:
        return
    for pid, name, mandate in SEED_PORTFOLIOS:
        m = resolve_mandate(mandate)
        _PORTFOLIOS[pid] = InstitutionalPortfolioRecord(
            portfolio_id=pid,
            name=name,
            mandate_id=m["mandate_id"],
            policy_profile=m["policy_profile"],
            members=("analyst@agi", "pm@agi"),
            status="active",
        )


def register_portfolio(
    portfolio_id: str,
    *,
    name: str = "",
    mandate_id: str = "balanced",
    members: list[str] | tuple[str, ...] | None = None,
    client_ids: list[str] | tuple[str, ...] | None = None,
) -> InstitutionalPortfolioRecord:
    pid = str(portfolio_id or "").strip()
    if not pid:
        raise ValueError("portfolio_id required")
    m = resolve_mandate(mandate_id)
    rec = InstitutionalPortfolioRecord(
        portfolio_id=pid,
        name=name or pid,
        mandate_id=m["mandate_id"],
        policy_profile=m["policy_profile"],
        members=tuple(members or ("analyst@agi",)),
        client_ids=tuple(client_ids or ()),
        status="active",
    )
    _PORTFOLIOS[pid] = rec
    return rec


def get_portfolio(portfolio_id: str) -> Optional[InstitutionalPortfolioRecord]:
    return _PORTFOLIOS.get(str(portfolio_id or "").strip())


def list_portfolios() -> list[InstitutionalPortfolioRecord]:
    return sorted(_PORTFOLIOS.values(), key=lambda p: p.portfolio_id)


def attach_client(portfolio_id: str, client_id: str) -> Optional[InstitutionalPortfolioRecord]:
    rec = get_portfolio(portfolio_id)
    if not rec:
        return None
    clients = tuple(dict.fromkeys([*rec.client_ids, client_id]))
    updated = InstitutionalPortfolioRecord(
        portfolio_id=rec.portfolio_id,
        name=rec.name,
        mandate_id=rec.mandate_id,
        policy_profile=rec.policy_profile,
        client_ids=clients,
        members=rec.members,
        status=rec.status,
        diagnostics=rec.diagnostics,
    )
    _PORTFOLIOS[portfolio_id] = updated
    return updated


def catalog() -> list[dict[str, Any]]:
    return [p.to_dict() for p in list_portfolios()]


bootstrap_seed_portfolios()
