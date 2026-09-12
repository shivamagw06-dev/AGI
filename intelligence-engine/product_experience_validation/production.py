"""E2E-01 production façades — API / Mission Control / CLI."""

from __future__ import annotations

from typing import Any, Optional

from product_experience_validation.flags import flags_dict, is_enabled
from product_experience_validation.runner import run_validation, run_workflow
from product_experience_validation.schema import (
    E2E_PRODUCT,
    E2E_SPEC,
    E2E_VERSION,
    E2E_WORKSTREAM_ID,
    FAILURE_CODES,
    FREEZE_LOCKS,
    PASS_SCORE,
    PRIMARY_TICKER,
    PRODUCT_ENTRY,
    RUBRIC_WEIGHTS,
    WORKFLOWS,
)
from product_experience_validation import store as e2e_store

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": E2E_WORKSTREAM_ID,
        "product": E2E_PRODUCT,
        "version": E2E_VERSION,
        "role": "end_to_end_product_experience_validation",
        "not_an_engine": True,
        "not_a_benchmark": True,
        "not_an_office": True,
        "product_entry": PRODUCT_ENTRY,
        "primary_ticker": PRIMARY_TICKER,
        "pass_score": PASS_SCORE,
        "workflow_count": len(WORKFLOWS),
        "rubric_weights": dict(RUBRIC_WEIGHTS),
        "failure_codes": list(FAILURE_CODES),
        "freeze_locks": dict(FREEZE_LOCKS),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": E2E_SPEC,
        "brand": "AGI",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    m = e2e_store.metrics()
    latest = e2e_store.latest() or {}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": E2E_WORKSTREAM_ID,
        "product": E2E_PRODUCT,
        "version": E2E_VERSION,
        "panels": m.get("panels") or {},
        "metrics": m,
        "latest": {
            "passed": latest.get("passed"),
            "score": latest.get("score"),
            "failure_codes": latest.get("failure_codes"),
            "final_answer": latest.get("final_answer"),
            "as_of": latest.get("as_of"),
        },
        "workflows": [{"id": w["id"], "name": w["name"]} for w in WORKFLOWS],
        "spec": E2E_SPEC,
        "as_of": now_iso(),
    }


def run(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": E2E_WORKSTREAM_ID}
    body = payload or {}
    wf = body.get("workflow") or body.get("workflow_id")
    if wf:
        return {"ok": True, "workstream_id": E2E_WORKSTREAM_ID, "workflow": run_workflow(str(wf))}
    return run_validation(persist=True)


def report() -> dict[str, Any]:
    latest = e2e_store.latest()
    if not latest:
        latest = run_validation(persist=True)
    return {
        "ok": True,
        "workstream_id": E2E_WORKSTREAM_ID,
        "product": E2E_PRODUCT,
        "report": latest,
    }


def soft_slice_mission_control() -> dict[str, Any]:
    m = e2e_store.metrics()
    latest = e2e_store.latest() or {}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": E2E_WORKSTREAM_ID,
        "product": E2E_PRODUCT,
        "version": E2E_VERSION,
        "brand": "AGI",
        "not_an_engine": True,
        "not_a_benchmark": True,
        "panels": m.get("panels") or {},
        "metrics": m,
        "latest_score": latest.get("score"),
        "latest_passed": latest.get("passed"),
        "final_answer": latest.get("final_answer"),
    }


def admin_page() -> str:
    latest = e2e_store.latest() or {}
    score = latest.get("score", "—")
    passed = latest.get("passed")
    status = "PASS" if passed else ("FAIL" if passed is False else "NOT RUN")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"/><title>E2E-01 — AGI Product Experience</title>
<style>
body{{font-family:IBM Plex Sans,system-ui,sans-serif;margin:2rem;color:#12141a;background:#f7f8fa}}
h1{{font-family:Source Serif 4,Georgia,serif}}
.card{{background:#fff;border:1px solid #e6e8ee;border-radius:10px;padding:1.25rem;max-width:720px}}
.ok{{color:#1f6b4a}}.bad{{color:#9b2c2c}}
code{{background:#f1f3f7;padding:0.1rem 0.35rem;border-radius:4px}}
</style></head><body>
<div class="card">
<h1>E2E-01 — Institutional Product Experience Validation</h1>
<p>Validates the complete AGI product experience — not an intelligence engine.</p>
<p>Status: <strong class="{'ok' if passed else 'bad'}">{status}</strong> · Score: <strong>{score}</strong> / 90</p>
<p>Entry: <code>/agi</code> · Primary: Kotak Mahindra Bank</p>
<p>API: <code>POST /v1/product-experience/run</code></p>
</div></body></html>"""
