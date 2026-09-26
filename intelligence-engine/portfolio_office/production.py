"""PO-01 production façades — portfolio state only."""

from __future__ import annotations

from typing import Any, Optional

from portfolio_office.flags import flags_dict, is_enabled
from portfolio_office.schema import (
    PO01_OFFICE_ID,
    PO01_PRODUCT,
    PO01_RECOMMENDATION_POLICY,
    PO01_SPEC,
    PO01_SUBSYSTEM,
    PO01_VERSION,
    PO01_WORKSTREAM_ID,
)
from portfolio_office import store as pf_store
from portfolio_office.service import (
    compute_state,
    create_portfolio,
    import_holdings as import_holdings,  # re-export
    take_snapshot,
)
from portfolio_office.report import build_psr

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PO01_WORKSTREAM_ID,
        "office_id": PO01_OFFICE_ID,
        "product": PO01_PRODUCT,
        "subsystem": PO01_SUBSYSTEM,
        "version": PO01_VERSION,
        "domain": "portfolio",
        "role": "canonical_portfolio_state",
        "state_only": True,
        "optimises": False,
        "rebalances": False,
        "buy_sell": False,
        "valuation": False,
        "never_recalculates_fire": True,
        "snapshots_immutable": True,
        "recommendation_policy": PO01_RECOMMENDATION_POLICY,
        "consumes": ["Office SDK", "FIRE-05", "FIRE-06", "holdings", "company_master", "market_reference"],
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PO01_SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    m = pf_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PO01_WORKSTREAM_ID,
        "version": PO01_VERSION,
        "buy_sell": False,
        "panels": m.get("panels") or {},
        "metrics": m,
        "portfolios": [
            {
                "portfolio_id": p.get("portfolio_id"),
                "name": (p.get("metadata") or {}).get("name"),
                "holdings_n": len(p.get("holdings") or []),
            }
            for p in pf_store.list_portfolios()
        ],
        "spec": PO01_SPEC,
        "as_of": now_iso(),
    }


def get_portfolio(portfolio_id: str, **kwargs: Any) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": PO01_WORKSTREAM_ID}
    try:
        psr = build_psr(portfolio_id, fire05_map=kwargs.get("fire05_map"), fire06_map=kwargs.get("fire06_map"))
        return {
            "ok": True,
            "enabled": True,
            "workstream_id": PO01_WORKSTREAM_ID,
            "office_id": PO01_OFFICE_ID,
            "version": PO01_VERSION,
            "buy_sell": False,
            "office_response": psr,
            "portfolio": (psr.get("payload") or {}).get("portfolio"),
            "exposures": (psr.get("payload") or {}).get("exposures"),
            "concentration": (psr.get("payload") or {}).get("concentration"),
            "quality": (psr.get("payload") or {}).get("quality"),
            "execution": (psr.get("payload") or {}).get("execution"),
        }
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "workstream_id": PO01_WORKSTREAM_ID, "version": PO01_VERSION}


def get_holdings(portfolio_id: str) -> dict[str, Any]:
    pf = pf_store.resolve_portfolio(portfolio_id)
    if not pf:
        return {"ok": False, "error": f"portfolio not found: {portfolio_id}"}
    from portfolio_office.weights import apply_weights

    pf = apply_weights(pf)
    return {
        "ok": True,
        "workstream_id": PO01_WORKSTREAM_ID,
        "portfolio_id": pf.get("portfolio_id"),
        "holdings": pf.get("holdings") or [],
        "cash": pf.get("cash"),
        "totals": pf.get("totals"),
    }


def get_exposures(portfolio_id: str, **kwargs: Any) -> dict[str, Any]:
    try:
        state = compute_state(portfolio_id, **{k: kwargs[k] for k in ("fire05_map", "fire06_map") if k in kwargs})
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "workstream_id": PO01_WORKSTREAM_ID,
        "portfolio_id": portfolio_id,
        "exposures": state["exposures"],
    }


def get_quality(portfolio_id: str, **kwargs: Any) -> dict[str, Any]:
    try:
        state = compute_state(portfolio_id, **{k: kwargs[k] for k in ("fire05_map", "fire06_map") if k in kwargs})
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "workstream_id": PO01_WORKSTREAM_ID,
        "portfolio_id": portfolio_id,
        "quality": state["quality"],
        "rescores": False,
        "module": "FIRE-06",
    }


def get_concentration(portfolio_id: str, **kwargs: Any) -> dict[str, Any]:
    try:
        state = compute_state(portfolio_id, **{k: kwargs[k] for k in ("fire05_map", "fire06_map") if k in kwargs})
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {
        "ok": True,
        "workstream_id": PO01_WORKSTREAM_ID,
        "portfolio_id": portfolio_id,
        "concentration": state["concentration"],
    }


def create(payload: dict[str, Any]) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False}
    name = str(payload.get("name") or payload.get("portfolio_name") or "").strip()
    if not name:
        return {"ok": False, "error": "name required"}
    pf = create_portfolio(
        name=name,
        owner=payload.get("owner"),
        base_currency=str(payload.get("base_currency") or "INR"),
        benchmark=payload.get("benchmark"),
        inception_date=payload.get("inception_date"),
        description=payload.get("description"),
        status=str(payload.get("status") or "active"),
        portfolio_id=payload.get("portfolio_id"),
        holdings=payload.get("holdings") or [],
        cash_balance=float(payload.get("cash_balance") or payload.get("cash") or 0.0),
        cash_currency=payload.get("cash_currency"),
    )
    out = {
        "ok": True,
        "workstream_id": PO01_WORKSTREAM_ID,
        "version": PO01_VERSION,
        "portfolio": pf,
        "portfolio_id": pf.get("portfolio_id"),
    }
    try:
        from platform_event_bus.publisher import soft_publish
        from platform_event_bus.schema import EVENT_PORTFOLIO_UPDATED

        soft_publish(
            EVENT_PORTFOLIO_UPDATED,
            producer="po-01",
            payload={
                "portfolio_id": pf.get("portfolio_id"),
                "holdings_n": len(pf.get("holdings") or []),
            },
        )
    except Exception:
        pass
    return out


def snapshot(portfolio_id: str, payload: Optional[dict[str, Any]] = None, **kwargs: Any) -> dict[str, Any]:
    payload = payload or {}
    try:
        snap = take_snapshot(
            portfolio_id,
            kind=str(payload.get("kind") or "manual"),
            as_of=payload.get("as_of"),
            label=payload.get("label"),
            fire05_map=kwargs.get("fire05_map") or payload.get("fire05_map"),
            fire06_map=kwargs.get("fire06_map") or payload.get("fire06_map"),
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    out = {
        "ok": True,
        "workstream_id": PO01_WORKSTREAM_ID,
        "immutable": True,
        "snapshot": snap,
        "snapshot_id": snap.get("snapshot_id"),
    }
    try:
        from platform_event_bus.publisher import soft_publish
        from platform_event_bus.schema import EVENT_PORTFOLIO_SNAPSHOT_CREATED

        soft_publish(
            EVENT_PORTFOLIO_SNAPSHOT_CREATED,
            producer="po-01",
            payload={
                "portfolio_id": snap.get("portfolio_id"),
                "snapshot_id": snap.get("snapshot_id"),
                "kind": snap.get("kind"),
                "as_of": snap.get("as_of"),
                "immutable": True,
            },
        )
    except Exception:
        pass
    return out


def soft_slice_mission_control() -> dict[str, Any]:
    m = pf_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PO01_WORKSTREAM_ID,
        "office_id": PO01_OFFICE_ID,
        "product": PO01_PRODUCT,
        "version": PO01_VERSION,
        "buy_sell": False,
        "state_only": True,
        "panels": m.get("panels") or {},
        "metrics": m,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>PO-01 Portfolio Office</title></head>
<body>
<h1>PO-01 — Portfolio Office</h1>
<pre>{h}</pre>
<p>Canonical portfolio state. Immutable snapshots. No BUY/SELL. No optimiser.</p>
</body></html>"""


# Re-export helpers used by CLI/tests
__all__ = [
    "health",
    "dashboard",
    "get_portfolio",
    "get_holdings",
    "get_exposures",
    "get_quality",
    "get_concentration",
    "create",
    "snapshot",
    "import_holdings",
    "soft_slice_mission_control",
    "admin_page",
]
