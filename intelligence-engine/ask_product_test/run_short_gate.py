"""Report-only short gate: the zero-defect checks, run over their full universe.

Blocks nothing. No required check, no branch protection, no deployment
dependency. It exists to be watched while the underlying defects are remediated.

The universe, not the current count
-----------------------------------
The last full run counted 4 hallucinations and 2 wrong-company bindings. Those
are what is broken today, not what this gate tests. A gate scoped to the failing
cases would pass the moment those six were fixed and would not notice the
seventh. So it runs **every** J_impossible case and **every** identity-bearing
case, and requires the defect counters to be zero across all of them.

At the time of writing that is 395 of the bank's 500 cases: 50 J_impossible plus
345 that resolve an identity.

Determinism
-----------
The editorial provider is stubbed on every run, so what this measures is the
pipeline's own logic rather than a provider's variance or a credential's
absence. Failing to load the stub is an **infrastructure failure**, not a
NOT_RUN: a required lane that quietly downgrades to "did not run" when its
determinism source is missing is a lane that reports nothing while looking
green. NOT_RUN belongs to optional live-provider evaluation, where not running
is a legitimate outcome.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ask_product_test import routing_failure_taxonomy as tax  # noqa: E402
from ask_product_test import zero_defect_extract as zde  # noqa: E402

EXIT_OK = 0
EXIT_DEFECTS = 1
EXIT_INFRASTRUCTURE = 2

#: Wall-clock the gate aims to stay inside. Exceeding it is reported, not
#: failed - the gate is report-only, and a budget that fails the run would be
#: enforcement by the back door.
BUDGET_SECONDS = int(os.environ.get("SHORT_GATE_BUDGET_SEC") or 900)

ARTIFACT = "short_gate_zero_defect.json"


def _load_stub():
    """Install the deterministic provider into the real pipeline.

    Its absence is infrastructure, not a result. A required lane that downgrades
    to NOT_RUN when its determinism source is missing reports nothing while
    looking like it found nothing.
    """
    from ask_product_test import provider_stub

    probe = provider_stub.answer_for("probe", mode="honest")
    if not (probe.get("answer") or {}).get("summary"):
        raise ImportError("provider_stub returned no answer text")
    mode = (os.environ.get("ASK_TEST_MODE") or "contract").strip().lower()
    if mode != "inprocess":
        raise ImportError(
            f"ASK_TEST_MODE={mode!r}; the short gate must run the real pipeline. "
            "In contract mode the harness answers without reaching the engine, "
            "every case fails for the same reason, and a green result would mean "
            "nothing")
    if not provider_stub.install():
        raise ImportError(
            "could not install the stub into editorial.service.resolve_provider; "
            "without it the pipeline falls back to template output, which is not "
            "the product")
    return provider_stub


def _artifact_dir() -> Path:
    """This run's own directory, so nothing earlier can be read as ours."""
    run_id = (f"{os.environ.get('GITHUB_RUN_ID')}-{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}"
              if os.environ.get("GITHUB_RUN_ID") else str(int(time.time())))
    base = Path(os.environ.get("ASK_TEST_ARTIFACTS") or (ROOT / "artifacts"))
    path = base / "_runs" / run_id / "short_gate"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_report(results: List[Dict[str, Any]], *, elapsed: float,
                 cases_planned: int, stub_ok: bool) -> Dict[str, Any]:
    """Counters, unique failing cases, and categories - kept apart."""
    defects = zde.summarise(results, defects=zde.REQUIRED_DEFECTS, provider_ok=stub_ok)
    categories = tax.classify(results)

    # A case can carry several labels. Counting labels as cases overstates the
    # problem; counting cases as labels hides which problems are present. Both
    # are reported, and neither is derived from the other.
    failing_cases = {r.get("id") for r in results if r.get("failed")}
    p0_cases = {r.get("id") for r in results
                if any(tax.categorise(l) in tax.RELEASE_CRITICAL
                       for l in (r.get("failed") or []))}

    non_p0 = {c: n for c, n in categories["by_category"].items()
              if c not in tax.RELEASE_CRITICAL}

    return {
        "suite": "short_gate_zero_defect",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_only": True,
        "blocks_merge": False,
        "blocks_deployment": False,
        "required_check": False,
        "section_mapping": "PROVISIONAL — awaiting product owner approval",
        "provider": "deterministic stub",
        "cases_planned": cases_planned,
        "cases_evaluated": len(results),
        "elapsed_seconds": round(elapsed, 1),
        "budget_seconds": BUDGET_SECONDS,
        "within_budget": elapsed <= BUDGET_SECONDS,
        # unique cases, held separately from label counts
        "unique_failing_cases": len(failing_cases),
        "unique_p0_cases": len(p0_cases),
        "label_occurrences": categories["labels_total"],
        # P0
        "defects": defects["defects"],
        "zero_defect": all(v == 0 for v in defects["defects"].values()),
        "offenders": defects["offenders"],
        "not_section_confined": defects["not_section_confined"],
        # preserved, and explicitly not P0
        "non_p0_categories": non_p0,
        "non_p0_note": ("routing and missing-metadata results are kept because "
                        "they are real and tracked, and separate because they "
                        "do not make a release unsafe"),
        "by_category": categories["by_category"],
        "decision": "PASS" if all(v == 0 for v in defects["defects"].values()) else "FAIL",
    }


def main() -> int:
    from ask_product_test.core_platform_acceptance_v1 import build_cases, evaluate_case

    try:
        _load_stub()
    except Exception as exc:
        # Infrastructure, not NOT_RUN. The lane cannot be deterministic without
        # its determinism source, and reporting "did not run" would let a
        # missing stub pass for an absence of findings.
        print(f"[short_gate] INFRASTRUCTURE: could not load the deterministic "
              f"stub: {type(exc).__name__}: {exc}", flush=True)
        return EXIT_INFRASTRUCTURE

    cases = zde.select_cases(build_cases(), defects=zde.REQUIRED_DEFECTS)
    print(f"[short_gate] {len(cases)} cases — every J_impossible and every "
          f"identity-bearing case, not only the ones failing today", flush=True)

    # The real pipeline, with only the editorial provider fixed. Routing,
    # retrieval, identity resolution and metadata all still run - they are what
    # the zero-defect checks are about. Feeding evaluate_case a canned payload
    # instead would measure the detector against its own fixture and report a
    # green result that means nothing.
    from ask_product_test.harness import AskProductHarness

    harness = AskProductHarness(
        latency_budget_ms=int(os.environ.get("ASK_TEST_LATENCY_MS") or "120000"))
    t0 = time.perf_counter()
    results: List[Dict[str, Any]] = []
    for i, case in enumerate(cases, 1):
        transport = harness.ask(case["question"], case=case)
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        results.append(evaluate_case(case, payload, int(transport.get("latency_ms") or 0)))
        if i % 50 == 0:
            print(f"  … {i}/{len(cases)}  ({time.perf_counter()-t0:.0f}s)", flush=True)
    elapsed = time.perf_counter() - t0

    report = build_report(results, elapsed=elapsed, cases_planned=len(cases),
                          stub_ok=True)
    out = _artifact_dir() / ARTIFACT
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n[short_gate] decision={report['decision']} "
          f"zero_defect={report['zero_defect']} "
          f"unique_failing_cases={report['unique_failing_cases']} "
          f"unique_p0_cases={report['unique_p0_cases']} "
          f"labels={report['label_occurrences']}", flush=True)
    print(f"[short_gate] defects={report['defects']}", flush=True)
    print(f"[short_gate] non-P0 (tracked, not blocking)={report['non_p0_categories']}",
          flush=True)
    print(f"[short_gate] {report['elapsed_seconds']}s of {BUDGET_SECONDS}s budget "
          f"(within={report['within_budget']})", flush=True)
    print(f"[short_gate] artifact: {out}", flush=True)
    print("[short_gate] report-only: blocks no merge and no deployment", flush=True)
    return EXIT_OK if report["zero_defect"] else EXIT_DEFECTS


if __name__ == "__main__":
    raise SystemExit(main())
