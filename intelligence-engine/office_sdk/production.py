"""Office SDK production façades — catalog / health / dispatch."""

from __future__ import annotations

from typing import Any

from office_sdk.domains import list_domains
from office_sdk.flags import flags_dict, is_enabled
from office_sdk.registry import catalog, dispatch, get_office
from office_sdk.schema import (
    SDK_PRODUCT,
    SDK_RECOMMENDATION_POLICY,
    SDK_SPEC,
    SDK_SUBSYSTEM,
    SDK_VERSION,
    SDK_WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    cat = catalog()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": SDK_WORKSTREAM_ID,
        "product": SDK_PRODUCT,
        "subsystem": SDK_SUBSYSTEM,
        "version": SDK_VERSION,
        "role": "shared_office_contract",
        "orchestrates_only": True,
        "buy_sell": False,
        "valuation": False,
        "never_recalculates": True,
        "live_offices": [o["office_id"] for o in cat.get("live_offices") or []],
        "planned_offices": [o["office_id"] for o in cat.get("planned_offices") or []],
        "dispatchable": cat.get("dispatchable"),
        "domains": [d["domain"] for d in cat.get("domains") or []],
        "recommendation_policy": SDK_RECOMMENDATION_POLICY,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": SDK_SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    cat = catalog()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": SDK_WORKSTREAM_ID,
        "version": SDK_VERSION,
        "panels": {
            "domains": len(cat.get("domains") or []),
            "live_offices": len(cat.get("live_offices") or []),
            "planned_offices": len(cat.get("planned_offices") or []),
            "dispatchable": cat.get("dispatchable"),
        },
        "catalog": cat,
        "buy_sell": False,
        "spec": SDK_SPEC,
        "as_of": now_iso(),
    }


def domains() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": SDK_WORKSTREAM_ID,
        "version": SDK_VERSION,
        "domains": list_domains(),
    }


def office_catalog() -> dict[str, Any]:
    return {"ok": True, "workstream_id": SDK_WORKSTREAM_ID, "version": SDK_VERSION, **catalog()}


def invoke(request: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a shared OfficeRequest to a live office."""
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": SDK_WORKSTREAM_ID, "version": SDK_VERSION}
    try:
        return dispatch(request)
    except ValueError as exc:
        return {
            "ok": False,
            "error": str(exc),
            "workstream_id": SDK_WORKSTREAM_ID,
            "version": SDK_VERSION,
            "office": get_office(str(request.get("office_id") or "")),
        }


def soft_slice_mission_control() -> dict[str, Any]:
    cat = catalog()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": SDK_WORKSTREAM_ID,
        "product": SDK_PRODUCT,
        "version": SDK_VERSION,
        "panels": {
            "domains": len(cat.get("domains") or []),
            "live_offices": len(cat.get("live_offices") or []),
            "planned_offices": len(cat.get("planned_offices") or []),
            "dispatchable": list(cat.get("dispatchable") or []),
        },
        "buy_sell": False,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Office SDK</title></head>
<body>
<h1>Office SDK — Shared Application Contract</h1>
<pre>{h}</pre>
<p>Common OfficeRequest / OfficeResponse for Research, Portfolio, Market, Execution, Knowledge domains.</p>
</body></html>"""
