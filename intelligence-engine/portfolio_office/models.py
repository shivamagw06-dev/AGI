"""Portfolio domain models — state representation only."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (name or "").strip()).strip("-").lower()
    return s or "portfolio"


def portfolio_metadata(
    *,
    portfolio_id: Optional[str] = None,
    name: str,
    owner: Optional[str] = None,
    base_currency: str = "INR",
    benchmark: Optional[str] = None,
    inception_date: Optional[str] = None,
    description: Optional[str] = None,
    status: str = "active",
) -> dict[str, Any]:
    pid = (portfolio_id or _slug(name)).strip()
    return {
        "schema": "po01.portfolio_metadata.v1",
        "portfolio_id": pid,
        "name": name.strip() or pid,
        "owner": owner,
        "base_currency": (base_currency or "INR").upper(),
        "benchmark": benchmark,
        "inception_date": inception_date,
        "description": description,
        "status": status if status in ("active", "closed", "draft") else "active",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }


def holding(
    *,
    ticker: str,
    company: Optional[str] = None,
    isin: Optional[str] = None,
    quantity: float = 0.0,
    average_cost: float = 0.0,
    current_market_value: Optional[float] = None,
    weight: Optional[float] = None,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    market_cap_bucket: Optional[str] = None,
    currency: Optional[str] = None,
    extras: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    t = str(ticker or "").strip().upper()
    qty = float(quantity or 0.0)
    avg = float(average_cost or 0.0)
    mv = float(current_market_value) if current_market_value is not None else qty * avg
    row: dict[str, Any] = {
        "schema": "po01.holding.v1",
        "ticker": t,
        "company": company or t,
        "isin": isin,
        "quantity": qty,
        "average_cost": avg,
        "current_market_value": float(mv),
        "weight": float(weight) if weight is not None else None,
        "sector": sector or "Unknown",
        "industry": industry or "Unknown",
        "country": (country or "Unknown").upper() if country else "Unknown",
        "market_cap_bucket": market_cap_bucket or "Unknown",
        "currency": (currency or "").upper() or None,
    }
    if extras:
        row["extras"] = dict(extras)
    return row


def cash_position(
    *,
    balance: float = 0.0,
    currency: str = "INR",
    weight: Optional[float] = None,
) -> dict[str, Any]:
    return {
        "schema": "po01.cash_position.v1",
        "balance": float(balance or 0.0),
        "currency": (currency or "INR").upper(),
        "weight": float(weight) if weight is not None else None,
    }


def portfolio(
    *,
    metadata: Mapping[str, Any],
    holdings: Optional[Sequence[Mapping[str, Any]]] = None,
    cash: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    meta = dict(metadata)
    holds = [dict(h) for h in (holdings or [])]
    cash_pos = dict(cash) if cash else cash_position(currency=meta.get("base_currency") or "INR")
    return {
        "schema": "po01.portfolio.v1",
        "metadata": meta,
        "portfolio_id": meta.get("portfolio_id"),
        "holdings": holds,
        "cash": cash_pos,
        "updated_at": _now_iso(),
    }


def snapshot_id(portfolio_id: str, as_of: str, kind: str) -> str:
    raw = f"{portfolio_id}|{as_of}|{kind}|{uuid.uuid4().hex[:8]}"
    return "snap:" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def portfolio_snapshot(
    *,
    portfolio_obj: Mapping[str, Any],
    kind: str = "manual",
    as_of: Optional[str] = None,
    label: Optional[str] = None,
    computed: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Immutable point-in-time portfolio state. Never mutate after creation."""
    as_of_iso = as_of or _now_iso()
    pid = str(portfolio_obj.get("portfolio_id") or (portfolio_obj.get("metadata") or {}).get("portfolio_id"))
    kind_n = kind if kind in ("current", "daily", "manual", "historical") else "manual"
    body = {
        "schema": "po01.portfolio_snapshot.v1",
        "snapshot_id": snapshot_id(pid, as_of_iso, kind_n),
        "portfolio_id": pid,
        "kind": kind_n,
        "as_of": as_of_iso,
        "label": label,
        "immutable": True,
        "created_at": _now_iso(),
        # Deep-copy state so later mutations to live portfolio cannot alter history
        "portfolio": deepcopy(dict(portfolio_obj)),
        "computed": deepcopy(dict(computed or {})),
    }
    # Fingerprint for audit/reproducibility
    fingerprint_src = {
        "portfolio_id": pid,
        "as_of": as_of_iso,
        "kind": kind_n,
        "holdings": body["portfolio"].get("holdings"),
        "cash": body["portfolio"].get("cash"),
        "computed_keys": sorted((body["computed"] or {}).keys()),
    }
    body["content_hash"] = hashlib.sha256(
        json.dumps(fingerprint_src, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return body
