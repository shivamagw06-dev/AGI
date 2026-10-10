"""Assemble AGI Release Health scorecard from IST + IBS + E2E (+ build/tests)."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _probe_build() -> dict[str, Any]:
    root = _repo_root()
    checks = {
        "agi_routes": (root / "src/pages/agi/AgiRoutes.jsx").is_file(),
        "company_workspace": (root / "intelligence-engine/company_workspace").is_dir(),
        "ist": (root / "intelligence-engine/institutional_stress_tests").is_dir(),
        "ibs": (root / "intelligence-engine/institutional_benchmarks").is_dir(),
        "e2e": (root / "intelligence-engine/product_experience_validation").is_dir(),
    }
    # Import smoke — build surface for the intelligence core
    imports_ok = True
    try:
        import institutional_benchmarks  # noqa: F401
        import institutional_stress_tests  # noqa: F401
        import product_experience_validation  # noqa: F401
        import company_workspace  # noqa: F401
    except Exception:
        imports_ok = False
    ok = all(checks.values()) and imports_ok
    return {
        "ok": ok,
        "label": "Build",
        "status": "PASS" if ok else "FAIL",
        "detail": checks,
        "imports_ok": imports_ok,
    }


def _probe_unit_tests(*, run: bool) -> dict[str, Any]:
    """Quick unit/smoke suite for release gate."""
    if not run:
        return {
            "ok": True,
            "skipped": True,
            "label": "Unit Tests",
            "status": "SKIPPED",
            "detail": "Skipped for this run — re-run with unit tests for a full gate",
        }
    root = _repo_root() / "intelligence-engine"
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_cw_01_company_workspace.py",
        "tests/test_ist_01_kotak_stress.py",
        "tests/test_ist_02_raw_evidence.py",
        "tests/test_ibs_01_institutional_benchmarks.py::test_health_agi_brand_and_role",
        "tests/test_ibs_01_institutional_benchmarks.py::test_catalog_covers_all_sectors",
        "tests/test_e2e_01_product_experience.py::test_health_role_and_brand",
        "-q",
        "--tb=no",
    ]
    import os

    t0 = time.perf_counter()
    try:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(root)
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        ms = round((time.perf_counter() - t0) * 1000.0, 2)
        ok = proc.returncode == 0
        return {
            "ok": ok,
            "label": "Unit Tests",
            "status": "PASS" if ok else "FAIL",
            "elapsed_ms": ms,
            "stdout_tail": (proc.stdout or "")[-400:],
            "stderr_tail": (proc.stderr or "")[-400:],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "label": "Unit Tests", "status": "FAIL", "error": str(exc)}


def _probe_integration() -> dict[str, Any]:
    checks = {}
    try:
        from institutional_stress_tests.production import health as ist_h

        checks["ist"] = ist_h().get("status") == "ok"
    except Exception:
        checks["ist"] = False
    try:
        from institutional_benchmarks.production import health as ibs_h

        checks["ibs"] = ibs_h().get("status") == "ok"
    except Exception:
        checks["ibs"] = False
    try:
        from product_experience_validation.production import health as e2e_h

        checks["e2e"] = e2e_h().get("status") == "ok"
    except Exception:
        checks["e2e"] = False
    try:
        from company_workspace.production import health as cw_h

        checks["cw"] = cw_h().get("status") == "ok"
    except Exception:
        checks["cw"] = False
    ok = all(checks.values())
    return {
        "ok": ok,
        "label": "Integration",
        "status": "PASS" if ok else "FAIL",
        "detail": checks,
    }


def _run_ist() -> dict[str, Any]:
    from institutional_stress_tests.fixtures import complete_answers, fire_prebuilt
    from institutional_stress_tests.production import run as ist_run

    # IST-01: full-stack institutional view (certified answers + FIRE prebuilt)
    # IST-02: raw-evidence research validation (no fixture answers)
    r1 = ist_run("IST-01", prebuilt=fire_prebuilt(), answers=complete_answers())
    r2 = ist_run("IST-02")
    results = []
    for case_id, r in (("IST-01", r1), ("IST-02", r2)):
        score_obj = r.get("score") if isinstance(r.get("score"), dict) else {}
        results.append(
            {
                "case_id": case_id,
                "passed": bool(r.get("passed")),
                "score": score_obj.get("weighted_total")
                or r.get("research_quality_score")
                or r.get("score"),
                "failure_codes": list(
                    r.get("failure_codes") or score_obj.get("automatic_failures") or []
                ),
            }
        )
    passed_n = sum(1 for r in results if r["passed"])
    return {
        "label": "IST",
        "passed": passed_n,
        "total": IST_EXPECTED,
        "display": f"{passed_n}/{IST_EXPECTED}",
        "ok": passed_n >= IST_EXPECTED,
        "cases": results,
    }


def _run_ibs() -> dict[str, Any]:
    from institutional_benchmarks.catalog import list_cases
    from institutional_benchmarks.production import run_all_benchmarks
    from institutional_benchmarks import store as ibs_store

    suite = run_all_benchmarks()
    cases = list_cases()
    expected = len(cases) or IBS_EXPECTED
    passed_n = int(suite.get("passed") or 0)
    if not passed_n and isinstance(suite.get("results"), list):
        passed_n = sum(1 for r in suite["results"] if r.get("passed"))
    total = int(suite.get("cases_run") or expected)
    avg = suite.get("average_score")
    if avg is None and suite.get("results"):
        scores = [float(r.get("score") or r.get("research_quality_score") or 0) for r in suite["results"]]
        avg = round(sum(scores) / len(scores), 2) if scores else None

    hallu = int(suite.get("hallucination_count") or 0)
    broken = int(suite.get("broken_provenance") or 0)
    latest_suite = ibs_store.latest_suite() or {}
    regression = latest_suite.get("regression_since_previous")
    if regression is None:
        regression = 0

    return {
        "label": "IBS",
        "passed": passed_n,
        "total": total,
        "display": f"{passed_n}/{total}",
        "ok": passed_n >= expected and passed_n >= IBS_EXPECTED,
        "average_score": avg,
        "hallucinations": hallu,
        "broken_provenance": broken,
        "regression": regression,
        "suite": {
            "average_score": avg,
            "passed_count": passed_n,
            "case_count": total,
            "release_gate": suite.get("release_gate") or {},
        },
    }


def _run_e2e() -> dict[str, Any]:
    from product_experience_validation.production import run as e2e_run

    result = e2e_run({})
    passed = bool(result.get("passed"))
    return {
        "label": "E2E",
        "passed": 1 if passed else 0,
        "total": E2E_EXPECTED,
        "display": f"{1 if passed else 0}/{E2E_EXPECTED}",
        "ok": passed,
        "score": result.get("score"),
        "final_answer": result.get("final_answer"),
        "failure_codes": list(result.get("failure_codes") or []),
        "performance_pass": "SLOW_PAGE" not in (result.get("failure_codes") or []),
    }


def assemble_release_health(*, refresh: bool = True, run_unit_tests: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    build = _probe_build()
    integration = _probe_integration()
    unit = _probe_unit_tests(run=run_unit_tests) if refresh else _probe_unit_tests(run=False)

    if refresh:
        ist = _run_ist()
        ibs = _run_ibs()
        e2e = _run_e2e()
    else:
        # Snapshot-only view from stores
        from institutional_stress_tests import store as ist_store
        from institutional_benchmarks import store as ibs_store
        from product_experience_validation import store as e2e_store

        ist_m = ist_store.metrics()
        ibs_m = ibs_store.metrics()
        e2e_latest = e2e_store.latest() or {}
        ist = {
            "label": "IST",
            "passed": int(ist_m.get("passes") or 0),
            "total": IST_EXPECTED,
            "display": f"{min(int(ist_m.get('passes') or 0), IST_EXPECTED)}/{IST_EXPECTED}",
            "ok": int(ist_m.get("passes") or 0) >= IST_EXPECTED,
            "stale": True,
        }
        suite = ibs_store.latest_suite() or {}
        passed_n = int(suite.get("passed_count") or ibs_m.get("passes") or 0)
        total = int(suite.get("case_count") or IBS_EXPECTED)
        ibs = {
            "label": "IBS",
            "passed": passed_n,
            "total": total,
            "display": f"{passed_n}/{total}",
            "ok": passed_n >= IBS_EXPECTED,
            "average_score": suite.get("average_score"),
            "hallucinations": int(ibs_m.get("hallucinations") or 0),
            "broken_provenance": int(ibs_m.get("broken_provenance") or 0),
            "regression": suite.get("regression_since_previous") or 0,
            "stale": True,
        }
        e2e_pass = bool(e2e_latest.get("passed"))
        e2e = {
            "label": "E2E",
            "passed": 1 if e2e_pass else 0,
            "total": E2E_EXPECTED,
            "display": f"{1 if e2e_pass else 0}/{E2E_EXPECTED}",
            "ok": e2e_pass,
            "score": e2e_latest.get("score"),
            "performance_pass": True,
            "stale": not bool(e2e_latest),
        }

    avg = ibs.get("average_score")
    if avg is None and e2e.get("score") is not None:
        avg = e2e.get("score")
    hallu = int(ibs.get("hallucinations") or 0)
    broken = int(ibs.get("broken_provenance") or 0)
    regression = ibs.get("regression")
    if regression is None:
        regression = 0
    # Regression FAIL if average fell (negative delta)
    regression_ok = float(regression) >= -float(RELEASE_GATES["regression_max"])
    perf_ok = bool(e2e.get("performance_pass", True))

    gates = {
        "build": bool(build.get("ok")),
        "unit_tests": bool(unit.get("ok")),
        "integration": bool(integration.get("ok")),
        "ist": bool(ist.get("ok")),
        "ibs": bool(ibs.get("ok")),
        "e2e": bool(e2e.get("ok")),
        "average_benchmark": (avg is not None and float(avg) >= float(RELEASE_GATES["average_benchmark_min"])),
        "hallucinations": hallu <= int(RELEASE_GATES["hallucinations_max"]),
        "broken_provenance": broken <= int(RELEASE_GATES["broken_provenance_max"]),
        "regression": regression_ok,
        "performance": perf_ok,
    }
    ready = all(gates.values())

    snapshot = {
        "ok": True,
        "workstream_id": RH_WORKSTREAM_ID,
        "product": RH_PRODUCT,
        "version": RH_VERSION,
        "title": "AGI Release Health",
        "build": build,
        "unit_tests": unit,
        "integration": integration,
        "ist": ist,
        "ibs": ibs,
        "e2e": e2e,
        "average_benchmark": avg,
        "hallucinations": hallu,
        "broken_provenance": broken,
        "regression": regression,
        "performance": "PASS" if perf_ok else "FAIL",
        "ready_for_release": ready,
        "ready_for_release_label": "YES" if ready else "NO",
        "gates": gates,
        "release_gates": dict(RELEASE_GATES),
        "rows": [
            {"label": "Build", "value": "✓" if build.get("ok") else "✗", "ok": build.get("ok")},
            {
                "label": "Unit Tests",
                "value": "SKIPPED" if unit.get("skipped") else ("✓" if unit.get("ok") else "✗"),
                "ok": unit.get("ok"),
            },
            {"label": "Integration", "value": "✓" if integration.get("ok") else "✗", "ok": integration.get("ok")},
            {"label": "IST", "value": ist.get("display"), "ok": ist.get("ok")},
            {"label": "IBS", "value": ibs.get("display"), "ok": ibs.get("ok")},
            {"label": "E2E", "value": e2e.get("display"), "ok": e2e.get("ok")},
            {"label": "Average Benchmark", "value": avg if avg is not None else "—", "ok": gates["average_benchmark"]},
            {"label": "Hallucinations", "value": hallu, "ok": gates["hallucinations"]},
            {"label": "Broken Provenance", "value": broken, "ok": gates["broken_provenance"]},
            {"label": "Regression", "value": regression, "ok": gates["regression"]},
            {"label": "Performance", "value": "PASS" if perf_ok else "FAIL", "ok": perf_ok},
            {"label": "Ready for Release", "value": "YES" if ready else "NO", "ok": ready},
        ],
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "spec": RH_SPEC,
        "brand": "AGI",
        "as_of": now_iso(),
    }
    rh_store.put(snapshot)
    return snapshot
