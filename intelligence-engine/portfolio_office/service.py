"""Portfolio state service — create / update holdings / compute / snapshot."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from portfolio_office.concentration import compute_concentration
from portfolio_office.execution import aggregate_execution
from portfolio_office.exposures import compute_exposures
from portfolio_office.models import (
    cash_position,
    holding,
    portfolio,
    portfolio_metadata,
    portfolio_snapshot,
)
from portfolio_office.quality import aggregate_quality
from portfolio_office import store as pf_store
from portfolio_office.weights import apply_weights


def create_portfolio(
    *,
    name: str,
    owner: Optional[str] = None,
    base_currency: str = "INR",
    benchmark: Optional[str] = None,
    inception_date: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "active",
    portfolio_id: Optional[str] = None,
    holdings: Optional[Sequence[Mapping[str, Any]]] = None,
    cash_balance: float = 0.0,
    cash_currency: Optional[str] = None,
) -> dict[str, Any]:
    meta = portfolio_metadata(
        portfolio_id=portfolio_id,
        name=name,
        owner=owner,
        base_currency=base_currency,
        benchmark=benchmark,
        inception_date=inception_date,
        description=description,
        status=status,
    )
    holds = []
    for h in holdings or []:
        if isinstance(h, Mapping):
            holds.append(
                holding(
                    ticker=str(h.get("ticker") or ""),
                    company=h.get("company"),
                    isin=h.get("isin"),
                    quantity=float(h.get("quantity") or 0.0),
                    average_cost=float(h.get("average_cost") or h.get("avg_cost") or 0.0),
                    current_market_value=h.get("current_market_value")
                    if h.get("current_market_value") is not None
                    else h.get("market_value"),
                    sector=h.get("sector"),
                    industry=h.get("industry"),
                    country=h.get("country"),
                    market_cap_bucket=h.get("market_cap_bucket") or h.get("market_cap"),
                    currency=h.get("currency") or base_currency,
                )
            )
    cash = cash_position(
        balance=float(cash_balance or 0.0),
        currency=cash_currency or base_currency,
    )
    pf = apply_weights(portfolio(metadata=meta, holdings=holds, cash=cash))
    return pf_store.put_portfolio(pf)


def import_holdings(
    portfolio_id: str,
    holdings: Sequence[Mapping[str, Any]],
    *,
    replace: bool = True,
    cash_balance: Optional[float] = None,
) -> dict[str, Any]:
    pf = pf_store.resolve_portfolio(portfolio_id)
    if not pf:
        raise ValueError(f"portfolio not found: {portfolio_id}")
    new_holds = []
    for h in holdings:
        new_holds.append(
            holding(
                ticker=str(h.get("ticker") or ""),
                company=h.get("company"),
                isin=h.get("isin"),
                quantity=float(h.get("quantity") or 0.0),
                average_cost=float(h.get("average_cost") or h.get("avg_cost") or 0.0),
                current_market_value=h.get("current_market_value")
                if h.get("current_market_value") is not None
                else h.get("market_value"),
                sector=h.get("sector"),
                industry=h.get("industry"),
                country=h.get("country"),
                market_cap_bucket=h.get("market_cap_bucket") or h.get("market_cap"),
                currency=h.get("currency") or (pf.get("metadata") or {}).get("base_currency"),
            )
        )
    if replace:
        pf["holdings"] = new_holds
    else:
        pf["holdings"] = list(pf.get("holdings") or []) + new_holds
    if cash_balance is not None:
        cash = dict(pf.get("cash") or {})
        cash["balance"] = float(cash_balance)
        pf["cash"] = cash
    pf = apply_weights(pf)
    return pf_store.put_portfolio(pf)


def compute_state(
    portfolio_id: str,
    *,
    fire05_map: Optional[Dict[str, Dict[str, Any]]] = None,
    fire06_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> dict[str, Any]:
    pf = pf_store.resolve_portfolio(portfolio_id)
    if not pf:
        raise ValueError(f"portfolio not found: {portfolio_id}")
    pf = apply_weights(pf)
    exposures = compute_exposures(pf)
    concentration = compute_concentration(pf)
    quality = aggregate_quality(pf, fire06_map=fire06_map)
    execution = aggregate_execution(pf, fire05_map=fire05_map)
    mean_conf = None
    confs = [quality.get("confidence"), execution.get("confidence")]
    confs_f = [float(c) for c in confs if isinstance(c, (int, float))]
    if confs_f:
        mean_conf = sum(confs_f) / len(confs_f)
    pf_store.record_metrics(
        quality_covered=bool(quality.get("holdings_covered")),
        exposure_covered=bool(exposures.get("sector")),
        mean_confidence=mean_conf,
    )
    # Persist weighted portfolio
    pf_store.put_portfolio(pf)
    return {
        "portfolio": pf,
        "exposures": exposures,
        "concentration": concentration,
        "quality": quality,
        "execution": execution,
        "confidence": {
            "mean_confidence": mean_conf or 0.0,
            "quality_confidence": quality.get("confidence"),
            "execution_confidence": execution.get("confidence"),
        },
    }


def take_snapshot(
    portfolio_id: str,
    *,
    kind: str = "manual",
    as_of: Optional[str] = None,
    label: Optional[str] = None,
    fire05_map: Optional[Dict[str, Dict[str, Any]]] = None,
    fire06_map: Optional[Dict[str, Dict[str, Any]]] = None,
) -> dict[str, Any]:
    state = compute_state(portfolio_id, fire05_map=fire05_map, fire06_map=fire06_map)
    snap = portfolio_snapshot(
        portfolio_obj=state["portfolio"],
        kind=kind,
        as_of=as_of,
        label=label,
        computed={
            "exposures": state["exposures"],
            "concentration": state["concentration"],
            "quality": state["quality"],
            "execution": state["execution"],
            "confidence": state["confidence"],
        },
    )
    return pf_store.put_snapshot(snap)
