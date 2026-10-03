"""RH-01 production façades."""

from __future__ import annotations

from typing import Any, Optional

from release_health.assemble import assemble_release_health
from release_health.flags import flags_dict, is_enabled
from release_health.schema import (
    E2E_EXPECTED,
    IBS_EXPECTED,
    IST_EXPECTED,
    RELEASE_GATES,
    RH_PRODUCT,
    RH_SPEC,
    RH_VERSION,
    RH_WORKSTREAM_ID,
)
from release_health import store as rh_store

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": RH_WORKSTREAM_ID,
        "product": RH_PRODUCT,
        "version": RH_VERSION,
        "role": "release_gate_dashboard",
        "not_an_engine": True,
        "aggregates": ["IST", "IBS", "E2E", "Build", "Unit Tests", "Integration"],
        "expected": {"ist": IST_EXPECTED, "ibs": IBS_EXPECTED, "e2e": E2E_EXPECTED},
        "release_gates": dict(RELEASE_GATES),
        "access": {
            "admin_ui": "/admin/release-health",
            "product_settings": "/agi/settings",
            "api_dashboard": "/v1/release-health/dashboard",
            "api_run": "POST /v1/release-health/run",
            "cli": "python3 -m release_health --run",
        },
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": RH_SPEC,
        "brand": "AGI",
        "as_of": now_iso(),
    }


def dashboard(*, refresh: bool = False) -> dict[str, Any]:
    """Serve the release-gate scorecard.

    Page loads must stay fast: never run pytest / full IST+IBS+E2E on a plain GET.
    - cached snapshot → return it
    - cold store → lightweight assemble from existing suite stores (no unit tests)
    - refresh=true → re-run suites without unit tests (POST /run for full gate)
    """
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": RH_WORKSTREAM_ID}
    latest = rh_store.latest()
    if refresh:
        latest = assemble_release_health(refresh=True, run_unit_tests=False)
    elif not latest:
        latest = assemble_release_health(refresh=False, run_unit_tests=False)
    return {
        "ok": True,
        "workstream_id": RH_WORKSTREAM_ID,
        "product": RH_PRODUCT,
        "version": RH_VERSION,
        "access": health()["access"],
        "snapshot": latest,
        "metrics": rh_store.metrics(),
        "as_of": now_iso(),
    }


def run(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": RH_WORKSTREAM_ID}
    body = payload or {}
    # Default off for HTTP — pytest alone can exceed BFF/browser timeouts on Render.
    # CLI / explicit UI opt-in still pass run_unit_tests=true.
    run_unit = body.get("run_unit_tests")
    if run_unit is None:
        run_unit = False
    snapshot = assemble_release_health(refresh=True, run_unit_tests=bool(run_unit))
    return snapshot


def soft_slice_mission_control() -> dict[str, Any]:
    latest = rh_store.latest() or {}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": RH_WORKSTREAM_ID,
        "product": RH_PRODUCT,
        "version": RH_VERSION,
        "ready_for_release": latest.get("ready_for_release"),
        "average_benchmark": latest.get("average_benchmark"),
        "panels": rh_store.metrics().get("panels") or {},
    }


def admin_page() -> str:
    latest = rh_store.latest() or {}
    ready = latest.get("ready_for_release_label") or "NOT RUN"
    avg = latest.get("average_benchmark", "—")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>AGI Release Health</title>
<meta http-equiv="refresh" content="0;url=/admin/release-health"/>
<style>body{{font-family:IBM Plex Sans,system-ui,sans-serif;margin:2rem}}</style>
</head><body>
<h1>AGI Release Health</h1>
<p>Ready: <strong>{ready}</strong> · Average Benchmark: <strong>{avg}</strong></p>
<p>Open the React dashboard: <a href="/admin/release-health">/admin/release-health</a></p>
</body></html>"""
