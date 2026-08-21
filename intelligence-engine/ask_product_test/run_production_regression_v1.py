#!/usr/bin/env python3
"""AGI Core v1.0 — Permanent Production Release Gate.

Runs the required suites together and writes a single release report.
Every future PR must PASS this gate before merge.

See:
  docs/AGI_CORE_V1_0.md
  ask_product_test/agi_core_v1_0.py
  ask_product_test/PRODUCTION_REGRESSION_V1.md

Suite order (permanent release policy — Core v1.0 + suites absorbed from main):
  1. Founder Evaluation V2         target ≥95%
  2. Golden Founder 5              target 5/5
  3. Golden Business 20            target 20/20
  4. Financial Intelligence (AFI)  target ≥95%
  5. Business Intelligence         target 100%
  6. Business Integration          target 100%
  7. Industry Acceptance           target 100%
  8. Industry Integration          target 100%
  9. Founder Evaluation V3         target ≥95%
 10. Coverage Acceptance           target PASS
 11. Concept Acceptance            target PASS
 12. Knowledge Unification         target PASS
 13. Recommendation Policy         target PASS
 14. Unknown Entity                target PASS
 15. Canonical Classification      target 100%
 16. Company Metadata Routing      target 100%
 17. Core Platform Acceptance      target ≥98% (zero-defect)
 18. Answer Quality                target ≥95%

Environment:
  ASK_TEST_MODE=inprocess|live|contract   (default inprocess)
  ASK_TEST_ARTIFACTS=/path/to/artifacts   (default: repo artifacts/)
  PROD_REGRESSION_QUICK=1                 skip coverage + AFI + heavy certs (local iteration only)
  PROD_REGRESSION_SKIP_AFI=1              skip AFI only (not merge-sufficient)

Exit 0 only when every included suite meets its target.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

from ask_product_test.agi_core_v1_0 import (  # noqa: E402
    AGI_CORE_OWNER,
    AGI_CORE_REGRESSION,
    AGI_CORE_STATUS,
    AGI_CORE_VERSION,
    RELEASE_GATE_ORDER,
    RELEASE_GATE_TARGETS,
    baseline_manifest,
)
from ask_product_test.acceptance_data import (  # noqa: E402
    apply_env_defaults,
    bootstrap_acceptance_data,
    check_acceptance_data,
)
from ask_product_test.harness import _artifacts_dir, mirror_artifact_dirs  # noqa: E402

# Exit codes: 0 = all pass, 1 = product failure, 2 = infrastructure failure
EXIT_INFRASTRUCTURE = 2

SUITE_MODULES: Dict[str, str] = {
    "founder_evaluation_v2": "ask_product_test.run_founder_evaluation_v2",
    "golden_founder_5": "ask_product_test.run_golden_founder_5",
    "golden_business_20": "ask_product_test.run_golden_business_20",
    "afi_acceptance": "ask_product_test.run_afi_acceptance_v1",
    "bi_acceptance": "ask_product_test.run_bi_acceptance_v1",
    "bi_integration": "ask_product_test.run_bi_integration_acceptance_v1",
    "ii_acceptance": "ask_product_test.run_industry_intelligence_acceptance_v1",
    "ii_integration": "ask_product_test.run_ii_integration_acceptance_v1",
    "founder_evaluation_v3": "ask_product_test.run_founder_evaluation_v3",
    "coverage_acceptance": "ask_product_test.run_coverage_acceptance_v1",
    "concept_acceptance": "ask_product_test.run_concept_acceptance_v1",
    "kul_acceptance": "ask_product_test.run_kul_acceptance_v1",
    "recommendation_policy": "ask_product_test.run_recommendation_policy_acceptance_v1",
    "unknown_entity": "ask_product_test.run_unknown_entity_acceptance_v1",
    "canonical_classification": "ask_product_test.run_canonical_classification_acceptance_v1",
    "company_metadata_routing": "ask_product_test.run_company_metadata_routing_acceptance_v1",
    "core_platform_acceptance": "ask_product_test.run_core_platform_acceptance_v1",
    "answer_quality": "ask_product_test.run_answer_quality_acceptance_v1",
}

SUITE_ARTIFACTS: Dict[str, str] = {
    "founder_evaluation_v2": "founder_evaluation_v2.json",
    "golden_founder_5": "golden_founder_5_latest.json",
    "golden_business_20": "golden_business_20.json",
    "afi_acceptance": "afi_acceptance_v1.json",
    "bi_acceptance": "bi_acceptance_v1.json",
    "bi_integration": "bi_integration_acceptance_v1.json",
    "ii_acceptance": "industry_intelligence_acceptance_v1.json",
    "ii_integration": "ii_integration_acceptance_v1.json",
    "founder_evaluation_v3": "founder_evaluation_v3.json",
    "coverage_acceptance": "coverage_acceptance_v1.json",
    "concept_acceptance": "concept_acceptance_v1.json",
    "kul_acceptance": "kul_acceptance_v1.json",
    "recommendation_policy": "recommendation_policy_acceptance_v1.json",
    "unknown_entity": "unknown_entity_acceptance_v1.json",
    "canonical_classification": "canonical_classification_acceptance_v1.json",
    "company_metadata_routing": "company_metadata_routing_acceptance_v1.json",
    "core_platform_acceptance": "core_platform_acceptance_v1.json",
    "answer_quality": "answer_quality_acceptance_v1.json",
}

# Heavy / slow suites skipped in quick local iteration (not merge-sufficient).
_QUICK_SKIP = {
    "coverage_acceptance",
    "afi_acceptance",
    "core_platform_acceptance",
    "answer_quality",
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _art() -> Path:
    return _artifacts_dir()


#: A suite that stops producing output must not take the whole job down with it.
#: Every suite today exits on its own - the slowest measured at 1,719s - so these
#: ceilings are headroom, not a schedule. They exist so a suite that hangs is
#: reported as a hung suite rather than consuming the 90-minute job timeout and
#: leaving no indication of which one stopped.
DEFAULT_SUITE_TIMEOUT_SEC = 900
SUITE_TIMEOUT_SEC: Dict[str, int] = {
    # measured 1,719s and 1,403s; the rest finish inside a minute
    "ask_product_test.run_core_platform_acceptance_v1": 3600,
    "ask_product_test.run_answer_quality_acceptance_v1": 3600,
    "ask_product_test.run_founder_evaluation_v2": 1800,
    "ask_product_test.run_golden_business_20": 1800,
}

#: Distinguishable from a suite that ran and failed. A timeout is a broken suite,
#: not a product score, and _decide must not read it as one.
EXIT_TIMEOUT = 124


def _suite_timeout(module: str) -> int:
    override = os.environ.get("GATE_SUITE_TIMEOUT_SEC")
    if override:
        try:
            return max(1, int(override))
        except ValueError:
            pass
    return SUITE_TIMEOUT_SEC.get(module, DEFAULT_SUITE_TIMEOUT_SEC)


def _group_is_empty(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        return True
    return False


def _terminate_group(pgid: Optional[int], module: str, *,
                     proc: "Optional[subprocess.Popen[bytes]]" = None) -> None:
    """Stop everything the suite started, whether or not the suite itself exited.

    Signalled by process group, not by pid. A suite that exits cleanly can still
    leave children running - which is what the job log's "Terminate orphan
    process: pid (2434) (python)" was: the runner host cleaning up after us. So
    this runs after every suite, not only after a timeout, and an already-empty
    group is the normal quiet case.
    """
    if pgid is None:
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        _reap(proc)
        return
    for signum, label in ((signal.SIGTERM, "SIGTERM"), (signal.SIGKILL, "SIGKILL")):
        if _group_is_empty(pgid):
            return
        try:
            os.killpg(pgid, signum)
        except (ProcessLookupError, PermissionError, OSError):
            return
        print(f"[gate] sent {label} to leftover {module} process group", flush=True)
        deadline = time.time() + 15
        while time.time() < deadline:
            # Reap our own child so it does not linger as a zombie holding the
            # group open, and so its status is available to the caller.
            if proc is not None and proc.poll() is None:
                try:
                    proc.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    pass
            if _group_is_empty(pgid):
                _reap(proc)
                return
            time.sleep(0.2)
    _reap(proc)


def _reap(proc: "Optional[subprocess.Popen[bytes]]") -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass


def _run_module(module: str, env: Optional[Dict[str, str]] = None) -> Tuple[int, float, float]:
    merged = os.environ.copy()
    merged.setdefault("ASK_TEST_MODE", "inprocess")
    merged.setdefault("ASK_TEST_CASE_COOLDOWN_SEC", "0")
    merged.setdefault("ASK_TEST_ARTIFACTS", str(_art()))
    if env:
        merged.update(env)
    limit = _suite_timeout(module)
    t0 = time.perf_counter()
    launched_at = time.time()
    print(f"\n========== RUN {module} (timeout {limit}s) ==========", flush=True)
    # start_new_session gives the suite its own process group so cleanup can
    # reach the children it spawned, not just the suite itself.
    proc = subprocess.Popen(
        [sys.executable, "-m", module],
        cwd=str(ROOT),
        env=merged,
        start_new_session=True,
    )
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = None
    timed_out = False
    try:
        returncode = proc.wait(timeout=limit)
    except subprocess.TimeoutExpired:
        timed_out = True
        returncode = EXIT_TIMEOUT
        print(f"[gate] TIMEOUT {module} after {time.perf_counter()-t0:.1f}s "
              f"(limit {limit}s)", flush=True)
    finally:
        # After every suite, not only after a timeout: a suite that exited
        # cleanly can still have left children behind.
        _terminate_group(pgid, module, proc=proc)
    elapsed = time.perf_counter() - t0
    label = "TIMEOUT" if timed_out else f"DONE {module} exit={returncode}"
    print(f"========== {label} ({elapsed:.1f}s) ==========", flush=True)
    return (EXIT_TIMEOUT if timed_out else returncode), elapsed, launched_at


def _purge_artifact(name: str) -> None:
    """Delete a suite's artifact before the suite runs.

    Without this, a suite that dies before writing leaves the previous run's
    file on disk and _decide reads it as this run's result. On a re-run of the
    same job that is last run's score, reported as though it were fresh - a
    green number produced by a suite that never finished.
    """
    for path in (_art() / name, Path("/workspace/artifacts") / name):
        try:
            path.unlink()
        except (FileNotFoundError, OSError):
            pass


def _artifact_is_fresh(name: str, launched_at: float) -> bool:
    """Whether the artifact on disk was written by the run that just finished."""
    for path in (_art() / name, Path("/workspace/artifacts") / name):
        try:
            if path.exists():
                # One second of slack for filesystem timestamp granularity.
                return path.stat().st_mtime >= (launched_at - 1.0)
        except OSError:
            continue
    return False


def _load(name: str) -> Dict[str, Any]:
    path = _art() / name
    if not path.exists():
        # Legacy cloud-agent path fallback.
        legacy = Path("/workspace/artifacts") / name
        if legacy.exists():
            path = legacy
        else:
            return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _decide(suite_id: str, report: Dict[str, Any], rc: int,
            launched_at: Optional[float] = None) -> Dict[str, Any]:
    """Normalize suite outcome against AGI Core v1.0 freeze targets."""
    target = dict(RELEASE_GATE_TARGETS[suite_id])
    target["artifact"] = SUITE_ARTIFACTS[suite_id]

    if rc == EXIT_TIMEOUT:
        return {
            "suite": suite_id,
            "pass": False,
            "actual": "timeout",
            "target": target,
            "failure_class": "TIMEOUT",
            "timed_out": True,
        }

    # A suite that died - signalled, crashed, killed by the OOM killer - has no
    # score either. A negative return code means a signal; anything outside the
    # runner's own vocabulary means the suite did not report an outcome, so its
    # artifact cannot be trusted to describe this run.
    abnormal = rc < 0 or rc not in (0, 1, EXIT_INFRASTRUCTURE)
    stale = (launched_at is not None
             and not report
             and not _artifact_is_fresh(target["artifact"], launched_at))
    if abnormal or stale:
        return {
            "suite": suite_id,
            "pass": False,
            "actual": f"no_result(rc={rc})" if abnormal else "stale_artifact",
            "target": target,
            "failure_class": "ABNORMAL_EXIT",
            "abnormal_exit": True,
        }

    data = report or _load(target["artifact"])
    metric = target["metric"]
    actual = data.get(metric)
    if actual is None and metric == "pass_rate_pct":
        if data.get("release_decision"):
            actual = 100.0 if data.get("release_decision") == "PASS" else 0.0
        elif data.get("total") and data.get("passed") is not None:
            actual = round(100.0 * float(data["passed"]) / float(data["total"]), 2)
        elif data.get("pass_rate") is not None:
            pr = float(data["pass_rate"])
            actual = round(pr * 100.0, 2) if pr <= 1.0 else pr
    if actual is None and metric == "pass_rate":
        if data.get("pass_rate") is not None:
            actual = float(data["pass_rate"])
        elif data.get("passed") is not None and data.get("total"):
            actual = float(data["passed"]) / float(data["total"])
    if actual is None and metric == "release_decision":
        # Coverage: accept PR-scoped PASS even when absolute decision is FAIL
        # on known pre-existing NSE twins (pr_451_scoped_decision).
        scoped = (
            data.get("pr_451_scoped_decision")
            or data.get("pr_scoped_decision")
            or data.get("pr_scoped")
            or (data.get("metrics") or {}).get("pr_scoped_decision")
        )
        if scoped == "PASS":
            actual = "PASS"
        else:
            actual = data.get("release_decision")

    if actual is None and metric == "overall_score_pct":
        metrics = data.get("metrics") or {}
        actual = metrics.get("overall_score_pct")
        if actual is None:
            actual = data.get("overall_score_pct")
        # Release gate nested under afi report.
        rg = data.get("release_gate") or {}
        if actual is None and isinstance(rg, dict):
            actual = (rg.get("metrics") or {}).get("overall_score_pct")
        if actual is None:
            actual = data.get("overall_score") or data.get("pass_rate_pct")

    if actual is None and metric == "overall_score":
        metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
        actual = data.get("overall_score") or metrics.get("overall_score")

    op = target["op"]
    value = target["value"]
    if actual is None:
        ok = rc == 0
        actual = "exit_ok" if ok else "exit_fail"
    elif op == "eq":
        if isinstance(value, str):
            ok = str(actual) == value
        else:
            try:
                ok = float(actual) == float(value)
            except (TypeError, ValueError):
                ok = rc == 0
    elif op == "gte":
        try:
            ok = float(actual) >= float(value)
        except (TypeError, ValueError):
            ok = rc == 0
    else:
        ok = rc == 0

    # Coverage special-case: prefer PR-scoped PASS from full artifact shape.
    if suite_id == "coverage_acceptance":
        pr_scoped = (
            data.get("pr_451_scoped_decision")
            or data.get("pr_scoped_decision")
            or data.get("pr_scoped")
        )
        if pr_scoped == "PASS" or (rc == 0 and data.get("release_decision") == "PASS"):
            ok = True
            actual = {
                "release_decision": data.get("release_decision"),
                "pr_scoped": pr_scoped or data.get("pr_451_scoped_decision"),
                "pass_rate_pct": data.get("pass_rate_pct"),
            }

    # Core Platform Acceptance also requires every zero-defect gate at zero —
    # a 98% score with a hallucination or wrong entity is still a release block.
    if suite_id == "core_platform_acceptance" and ok and data.get("zero_defect") is False:
        ok = False

    # Golden founder 5 also uses release_block / all-pass.
    if suite_id == "golden_founder_5":
        ok = (data.get("passed") == data.get("total") == 5) or (
            data.get("pass_rate") == 1.0 and not data.get("release_block")
        ) or (rc == 0 and data.get("passed") == 5)

    hard = data.get("hard_fail_flags") or {}
    hallucinations = 0
    if isinstance(hard, dict) and hard:
        hallucinations = len(hard)
    if suite_id in {"founder_evaluation_v2", "afi_acceptance"}:
        hallucinations = max(
            hallucinations,
            int(
                data.get("hallucination_count")
                or (data.get("metrics") or {}).get("hallucination_count")
                or 0
            ),
        )
    if suite_id in {"founder_evaluation_v2", "founder_evaluation_v3", "afi_acceptance"} and hallucinations:
        ok = False

    failure_class = "PRODUCT"
    if data.get("failure_class") == "INFRASTRUCTURE" or data.get("decision") == "NOT_EVALUATED":
        failure_class = "INFRASTRUCTURE"
        ok = False
        actual = data.get("decision") or "NOT_EVALUATED"
    elif rc == EXIT_INFRASTRUCTURE:
        failure_class = "INFRASTRUCTURE"
        ok = False
        actual = "NOT_EVALUATED"

    return {
        "suite": suite_id,
        "target": target,
        "actual": actual,
        "exit_code": rc,
        "pass": bool(ok),
        "failure_class": failure_class,
        "hallucination_or_hard_fail_count": hallucinations,
        "release_decision_artifact": data.get("release_decision") or data.get("decision"),
        "reason": data.get("reason"),
    }


def main() -> int:
    os.environ.setdefault("ASK_TEST_MODE", "inprocess")
    art = _art()
    os.environ.setdefault("ASK_TEST_ARTIFACTS", str(art))
    mirror_artifact_dirs()  # optional cloud-agent mirrors; never raises

    # Bootstrap + health check — deterministic acceptance dataset for CI/local parity
    skip_bootstrap = os.environ.get("SKIP_ACCEPTANCE_BOOTSTRAP", "").strip() in {"1", "true", "yes"}
    if not skip_bootstrap:
        try:
            bootstrap_acceptance_data(force=False, verbose=False)
        except Exception as exc:
            print(f"[production_regression_v1] bootstrap failed: {exc}", flush=True)

    apply_env_defaults()
    infra_health = check_acceptance_data(verbose=True)
    (art / "acceptance_data_health.json").write_text(
        json.dumps(infra_health, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    if infra_health.get("status") != "PASS":
        print(
            "\n[production_regression_v1] INFRASTRUCTURE FAILURE — acceptance data incomplete",
            flush=True,
        )
        print("[production_regression_v1] Regression not executed.", flush=True)
        return EXIT_INFRASTRUCTURE

    quick = os.environ.get("PROD_REGRESSION_QUICK", "").strip() in {"1", "true", "yes"}
    skip_afi = os.environ.get("PROD_REGRESSION_SKIP_AFI", "").strip() in {"1", "true", "yes"}
    # Permanent AGI Core v1.0 policy: AFI is on by default for merge gates.
    with_afi = True
    if "--quick" in sys.argv or quick:
        quick = True
        with_afi = False
    if "--skip-afi" in sys.argv or skip_afi:
        with_afi = False
    if "--with-afi" in sys.argv:
        with_afi = True
        quick = False

    plan: List[Tuple[str, str]] = []
    for suite_id in RELEASE_GATE_ORDER:
        if suite_id == "afi_acceptance" and not with_afi:
            continue
        if quick and suite_id in _QUICK_SKIP:
            continue
        module = SUITE_MODULES[suite_id]
        plan.append((suite_id, module))

    results: List[Dict[str, Any]] = []
    for suite_id, module in plan:
        # Removed before launch so a suite that never writes cannot be scored
        # from the file its previous run left behind.
        _purge_artifact(SUITE_ARTIFACTS[suite_id])
        rc, elapsed, launched_at = _run_module(module)
        decision = _decide(suite_id, {}, rc, launched_at=launched_at)
        decision["elapsed_sec"] = round(elapsed, 1)
        results.append(decision)
        print(
            f"[gate] {suite_id}: pass={decision['pass']} actual={decision['actual']} "
            f"target={decision['target']}",
            flush=True,
        )

    all_pass = all(r["pass"] for r in results)
    infra_failures = [r for r in results if r.get("failure_class") == "INFRASTRUCTURE"]
    timed_out = [r for r in results if r.get("failure_class") == "TIMEOUT"]
    abnormal = [r for r in results if r.get("failure_class") == "ABNORMAL_EXIT"]
    product_failures = [r for r in results
                        if not r["pass"]
                        and r.get("failure_class") not in
                        ("INFRASTRUCTURE", "TIMEOUT", "ABNORMAL_EXIT")]
    if timed_out:
        # Named explicitly. The failure this guards against is a suite that hangs
        # and is then read as a product regression.
        print(f"\n[gate] suites that timed out: {[r['suite'] for r in timed_out]}", flush=True)
    full_gate = bool(all_pass and with_afi and not quick)
    report = {
        "suite": "AGI Core v1.0 — Production Release Gate",
        "agi_core_version": AGI_CORE_VERSION,
        "status": AGI_CORE_STATUS,
        "owner": AGI_CORE_OWNER,
        "regression": AGI_CORE_REGRESSION,
        "timestamp": _ts(),
        "mode": os.environ.get("ASK_TEST_MODE"),
        "quick": quick,
        "with_afi": with_afi,
        "merge_allowed": full_gate,
        "acceptance_data_health": infra_health,
        "infrastructure": {
            "status": "PASS" if not infra_failures else "FAIL",
            "acceptance_dataset": infra_health.get("status"),
            "suite_failures": [r["suite"] for r in infra_failures],
        },
        "product": {
            "status": "PASS" if not product_failures else "FAIL",
            "suite_failures": [
                {"suite": r["suite"], "actual": r["actual"]} for r in product_failures
            ],
            "reason": (
                None
                if not product_failures
                else f"{product_failures[0]['suite']} below threshold (actual={product_failures[0]['actual']})"
            ),
        },
        "targets": {
            "Founder Evaluation V2": "≥95%",
            "Founder Evaluation V3": "≥95%",
            "Golden Founder 5": "5/5",
            "Golden Business 20": "20/20",
            "AFI": "≥95%",
            "BI Acceptance": "100%",
            "Business Integration": "100%",
            "Industry Acceptance": "100%",
            "Industry Integration": "100%",
            "Coverage": "PASS",
            "Concept": "PASS",
            "KUL": "PASS",
            "Recommendation Policy": "PASS",
            "Unknown Entity": "PASS",
            "Canonical Classification": "100%",
            "Company Metadata Routing": "100%",
            "Core Platform Acceptance": "≥98% + zero-defect",
            "Answer Quality": "≥95%",
            "Hallucinations": 0,
        },
        "suites": results,
        "passed_suites": sum(1 for r in results if r["pass"]),
        "total_suites": len(results),
        "release_decision": "PASS" if all_pass else "FAIL",
        "phase3_freeze_ready": full_gate,
        "phase31_freeze_ready": full_gate,
        "agi_core_v1_ready": full_gate,
        "baseline": baseline_manifest(),
        "note": (
            "AGI Core v1.0 permanent release policy: full Production Release Gate "
            "(including AFI + Coverage + industry/identity/platform certs) must PASS "
            "before merge. Quick mode is for local iteration only and is not merge-sufficient."
        ),
    }
    text = json.dumps(report, indent=2, default=str) + "\n"
    (art / "production_regression_v1.json").write_text(text, encoding="utf-8")
    for mirror in mirror_artifact_dirs()[1:]:
        try:
            (mirror / "production_regression_v1.json").write_text(text, encoding="utf-8")
        except OSError:
            pass
    print(
        f"\n[production_regression_v1] {report['passed_suites']}/{report['total_suites']} "
        f"decision={report['release_decision']} agi_core_v1_ready={report['agi_core_v1_ready']} "
        f"merge_allowed={report['merge_allowed']}",
        flush=True,
    )
    print("\nInfrastructure", flush=True)
    print(f"  Acceptance Dataset: {report['infrastructure']['acceptance_dataset']}", flush=True)
    if infra_failures:
        print(f"  Infrastructure suite failures: {[r['suite'] for r in infra_failures]}", flush=True)
    print("\nProduct", flush=True)
    for r in results:
        mark = "PASS" if r["pass"] else r.get("failure_class", "FAIL")
        print(f"  {r['suite']}: {r['actual']} [{mark}]", flush=True)
    if product_failures:
        print(f"\n  Product failure reason: {report['product']['reason']}", flush=True)
    # A suite that did not run outranks how the rest scored. Returning
    # EXIT_INFRASTRUCTURE here would file a hung suite under "infrastructure"
    # and hide it; merge_allowed is already False because all_pass is False.
    if timed_out:
        print(f"[gate] exiting {EXIT_TIMEOUT}: suite timeout", flush=True)
        return EXIT_TIMEOUT
    if abnormal:
        print("[gate] exiting 1: a suite produced no usable result", flush=True)
        return 1
    if infra_failures and not product_failures:
        return EXIT_INFRASTRUCTURE
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
