"""MPC-01 Client Registry — clients reference portfolios; intelligence stays shared."""

from __future__ import annotations

from typing import Any, Optional

from institutional_multi_portfolio.models import InstitutionalClient
from institutional_multi_portfolio.schema import SEED_CLIENTS
from institutional_multi_portfolio import portfolio_registry as preg

_CLIENTS: dict[str, InstitutionalClient] = {}


def reset_for_tests() -> None:
    _CLIENTS.clear()
    bootstrap_seed_clients()


def bootstrap_seed_clients() -> None:
    if _CLIENTS:
        return
    for cid, name, portfolios, policy in SEED_CLIENTS:
        _CLIENTS[cid] = InstitutionalClient(
            client_id=cid,
            client_name=name,
            portfolios=tuple(portfolios),
            policy_profile=policy,
        )
        for pid in portfolios:
            if preg.get_portfolio(pid):
                preg.attach_client(pid, cid)


def register_client(
    client_id: str,
    *,
    client_name: str = "",
    portfolios: list[str] | tuple[str, ...] | None = None,
    policy_profile: str = "family_office",
    publication_preferences: list[str] | tuple[str, ...] | None = None,
) -> InstitutionalClient:
    cid = str(client_id or "").strip()
    if not cid:
        raise ValueError("client_id required")
    ports = tuple(portfolios or ())
    client = InstitutionalClient(
        client_id=cid,
        client_name=client_name or cid,
        portfolios=ports,
        policy_profile=policy_profile,
        publication_preferences=tuple(
            publication_preferences or ("WeeklyClientReport", "MonthlyReview")
        ),
    )
    _CLIENTS[cid] = client
    for pid in ports:
        if preg.get_portfolio(pid):
            preg.attach_client(pid, cid)
        else:
            preg.register_portfolio(pid, name=pid, mandate_id="balanced", client_ids=[cid])
    return client


def get_client(client_id: str) -> Optional[InstitutionalClient]:
    return _CLIENTS.get(str(client_id or "").strip())


def list_clients() -> list[InstitutionalClient]:
    return sorted(_CLIENTS.values(), key=lambda c: c.client_id)


def catalog() -> list[dict[str, Any]]:
    return [c.to_dict() for c in list_clients()]


bootstrap_seed_clients()
