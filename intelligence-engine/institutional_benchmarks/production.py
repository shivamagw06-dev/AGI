"""IBS-01 production façades — API / Mission Control."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from institutional_benchmarks.catalog import get_case, list_cases, sectors
from institutional_benchmarks.consensus import compare_consensus
from institutional_benchmarks.flags import flags_dict, is_enabled
from institutional_benchmarks.pipeline import run_all, run_benchmark, run_sector
from institutional_benchmarks.schema import (
    CI_RELEASE_GATES,
    FAILURE_CODES,
    FREEZE_LOCKS,
    IBS_PRODUCT,
    IBS_SPEC,
    IBS_VERSION,
    IBS_WORKSTREAM_ID,
    PASS_SCORE,
    RUBRIC_WEIGHTS,
    SECTORS,
)
from institutional_benchmarks import store as ibs_store

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IBS_WORKSTREAM_ID,
        "product": IBS_PRODUCT,
        "version": IBS_VERSION,
        "role": "permanent_institutional_benchmark_framework",
        "not_an_engine": True,
        "not_an_office": True,
        "not_a_workspace": True,
        "not_a_validation_fixture": True,
        "raw_evidence_only": True,
        "no_fixture_answers": True,
        "pass_score": PASS_SCORE,
        "sectors": list(SECTORS),
        "case_count": len(list_cases()),
        "rubric_weights": dict(RUBRIC_WEIGHTS),
        "failure_codes": list(FAILURE_CODES),
        "freeze_locks": dict(FREEZE_LOCKS),
        "ci_release_gates": dict(CI_RELEASE_GATES),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": IBS_SPEC,
        "brand": "AGI",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    m = ibs_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IBS_WORKSTREAM_ID,
        "product": IBS_PRODUCT,
        "version": IBS_VERSION,
        "panels": m.get("panels") or {},
        "metrics": m,
        "sectors": sectors(),
        "latest_suite": ibs_store.latest_suite(),
        "ci_release_gates": dict(CI_RELEASE_GATES),
        "spec": IBS_SPEC,
        "as_of": now_iso(),
    }


def list_benchmarks(sector: Optional[str] = None) -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": IBS_WORKSTREAM_ID,
        "sector": sector,
        "cases": list_cases(sector=sector),
        "sectors": sectors(),
    }


def get_benchmark(case_id: str, *, cutoff: Optional[str] = None) -> dict[str, Any]:
    case = get_case(case_id, cutoff=cutoff)
    # Do not dump full document texts in GET by default — metadata + counts
    corpus = case.pop("corpus", {})
    return {
        "ok": True,
        "workstream_id": IBS_WORKSTREAM_ID,
        **case,
        "corpus_preview": {
            "document_count": corpus.get("document_count"),
            "historical_cutoff": corpus.get("historical_cutoff"),
            "evidence_ids": [d.get("evidence_id") for d in (corpus.get("documents") or [])[:12]],
        },
    }


def run(
    case_id: str,
    *,
    cutoff: Optional[str] = None,
    fixture_answers: Optional[Mapping[str, Any]] = None,
    consistency: bool = True,
    include_consensus: bool = False,
    house_notes: Optional[Sequence[Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": IBS_WORKSTREAM_ID}
    result = run_benchmark(
        case_id,
        cutoff=cutoff,
        fixture_answers=fixture_answers,
        consistency=consistency,
    )
    if include_consensus:
        result["consensus"] = compare_consensus(
            result.get("institutional_report") or {},
            house_notes=house_notes,
        )
    return result


def run_all_benchmarks(**kwargs: Any) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": IBS_WORKSTREAM_ID}
    return run_all(**kwargs)


def run_sector_benchmarks(sector: str, **kwargs: Any) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": IBS_WORKSTREAM_ID}
    return run_sector(sector, **kwargs)


def soft_slice_mission_control() -> dict[str, Any]:
    m = ibs_store.metrics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IBS_WORKSTREAM_ID,
        "product": IBS_PRODUCT,
        "version": IBS_VERSION,
        "brand": "AGI",
        "panels": m.get("panels") or {},
        "metrics": m,
        "ci_release_gates": dict(CI_RELEASE_GATES),
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>IBS-01 AGI Institutional Benchmarks</title></head>
<body>
<h1>IBS-01 — AGI Institutional Benchmark Suite</h1>
<pre>{h}</pre>
<p>Permanent benchmark framework for the AGI Intelligence Core. Raw evidence only. Not an engine.</p>
</body></html>"""
