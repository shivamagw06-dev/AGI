"""IST production façades — Mission Control / API."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from institutional_stress_tests.cases import list_cases
from institutional_stress_tests.flags import flags_dict, is_enabled
from institutional_stress_tests.pipeline_ist02 import run_ist02
from institutional_stress_tests.runner import run_case
from institutional_stress_tests.schema import (
    FAILURE_CODES,
    FREEZE_LOCKS,
    IST01_CASE_ID,
    IST01_SPEC,
    IST01_WORKSTREAM_ID,
    IST_VERSION,
    MODULE_CODE,
    NO_IST_ACTIONS,
    PROGRAMME,
    PROGRAMME_SHORT,
    REQUIRED_MODULES,
    RUBRIC_WEIGHTS,
)
from institutional_stress_tests.schema_ist02 import (
    IST02_CASE_ID,
    IST02_FAILURE_CODES,
    IST02_FREEZE_LOCKS,
    IST02_PASS_SCORE,
    IST02_RUBRIC_WEIGHTS,
    IST02_SPEC,
    IST02_WORKSTREAM_ID,
)
from institutional_stress_tests import store as ist_store

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "programme_short": PROGRAMME_SHORT,
        "module_code": MODULE_CODE,
        "workstream_id": IST01_WORKSTREAM_ID,
        "version": IST_VERSION,
        "primary_case": IST01_CASE_ID,
        "cases": [IST01_CASE_ID, IST02_CASE_ID],
        "no_single_module_pass": True,
        "forbids_buy_sell_verdict": True,
        "required_modules": list(REQUIRED_MODULES),
        "rubric_weights": dict(RUBRIC_WEIGHTS),
        "failure_codes": list(FAILURE_CODES),
        "no_actions": list(NO_IST_ACTIONS),
        "freeze_locks": dict(FREEZE_LOCKS),
        "ist02": {
            "workstream_id": IST02_WORKSTREAM_ID,
            "case_id": IST02_CASE_ID,
            "raw_evidence_only": True,
            "no_fixture_answers": True,
            "pass_score": IST02_PASS_SCORE,
            "rubric_weights": dict(IST02_RUBRIC_WEIGHTS),
            "failure_codes": list(IST02_FAILURE_CODES),
            "freeze_locks": dict(IST02_FREEZE_LOCKS),
            "spec": IST02_SPEC,
        },
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": IST01_SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    m = ist_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IST01_WORKSTREAM_ID,
        "version": IST_VERSION,
        "cases": [{"case_id": c.get("case_id"), "title": c.get("title")} for c in list_cases()],
        "panels": m.get("panels") or {},
        "metrics": m,
        "latest": ist_store.latest(),
        "spec": IST01_SPEC,
        "as_of": now_iso(),
    }


def run(
    case_id: str = IST01_CASE_ID,
    *,
    prebuilt: Optional[Mapping[str, Mapping[str, Any]]] = None,
    answers: Optional[Mapping[str, Any]] = None,
    final_view: Optional[Mapping[str, Any]] = None,
    modules_filter: Optional[Sequence[str]] = None,
    write_report: bool = False,
    corpus: Optional[Mapping[str, Any]] = None,
    fixture_answers: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": IST01_WORKSTREAM_ID}
    cid = str(case_id or IST01_CASE_ID).strip().upper()
    if cid in {IST02_CASE_ID, "IST02"}:
        result = run_ist02(IST02_CASE_ID, corpus=corpus, fixture_answers=fixture_answers)
    else:
        result = run_case(
            case_id,
            prebuilt=prebuilt,
            answers=answers,
            final_view=final_view,
            modules_filter=modules_filter,
        )
    if write_report:
        from institutional_stress_tests.reports import write_docs

        result["report_paths"] = write_docs(result)
    return result


def run_raw_evidence(
    case_id: str = IST02_CASE_ID,
    *,
    corpus: Optional[Mapping[str, Any]] = None,
    fixture_answers: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """IST-02 entrypoint — raw evidence only."""
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": IST02_WORKSTREAM_ID}
    return run_ist02(case_id, corpus=corpus, fixture_answers=fixture_answers)


def report(case_id: str = IST01_CASE_ID) -> dict[str, Any]:
    latest = ist_store.latest()
    if not latest or latest.get("case_id") != case_id:
        # Run a structural inventory-only pass (no fabricated answer → expect fail on answer contract)
        latest = run_case(case_id)
    from institutional_stress_tests.reports import build_markdown

    return {
        "ok": True,
        "case_id": case_id,
        "passed": latest.get("passed"),
        "markdown": build_markdown(latest),
        "score": latest.get("score"),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    m = ist_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IST01_WORKSTREAM_ID,
        "programme": PROGRAMME,
        "version": IST_VERSION,
        "no_single_module_pass": True,
        "panels": m.get("panels") or {},
        "metrics": m,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>IST-01 Institutional Stress Test</title></head>
<body>
<h1>IST-01 — Kotak / RBI Institutional Stress Test</h1>
<pre>{h}</pre>
<p>No individual module can pass. Orchestration required. Not BUY/SELL.</p>
</body></html>"""
