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

At the time of writing that is 395 of the core bank's 500 cases: 50
J_impossible plus 345 that resolve an identity. The six ambiguous/uncovered
namesake fallthrough cases from company-metadata routing are added separately;
they have no expected ticker by design, which is exactly why the core selector
cannot represent them.

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
from collections import Counter
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

#: The ceiling, in version control. Deliberately not readable from the
#: environment: a budget an environment variable can raise is a budget that gets
#: raised on the run that breaches it, and the number in the repository stops
#: describing what is enforced. Changing it is a commit and a review.
BUDGET_SECONDS = 900

#: A run may set a *lower* ceiling to fail faster locally. It may not set a
#: higher one - that is the whole point of the constant above.
def budget_seconds() -> int:
    override = (os.environ.get("SHORT_GATE_BUDGET_SEC") or "").strip()
    if not override:
        return BUDGET_SECONDS
    try:
        value = int(override)
    except ValueError:
        return BUDGET_SECONDS
    if value > BUDGET_SECONDS:
        print(f"[short_gate] ignoring SHORT_GATE_BUDGET_SEC={value}: the ceiling "
              f"is {BUDGET_SECONDS}s and is set in version control", flush=True)
        return BUDGET_SECONDS
    return max(1, value)


# --------------------------------------------------------------------------
# Partitioning
# --------------------------------------------------------------------------


def manifest(cases: List[Dict[str, Any]]) -> List[str]:
    """Every case id the extraction says must run, in order."""
    return sorted(str(c.get("id")) for c in cases)


TIMINGS_FILE = Path(__file__).resolve().parent / "case_timings.json"


def load_timings() -> Dict[str, float]:
    """Per-case seconds from an earlier run, if we have them.

    Written by the combine job and committed, so every pull request shards on
    the same measurements. A cache would not do: Actions caches created inside
    a pull request are scoped to that pull request and are invisible to the
    next one, so all but the first PR would still shard blind.
    """
    path = Path(os.environ.get("SHORT_GATE_TIMINGS") or TIMINGS_FILE)
    try:
        raw = json.loads(path.read_text())
    except Exception:
        return {}
    seconds = raw.get("case_seconds") if isinstance(raw, dict) else None
    if not isinstance(seconds, dict):
        return {}
    out: Dict[str, float] = {}
    for case_id, value in seconds.items():
        try:
            taken = float(value)
        except (TypeError, ValueError):
            continue
        if taken > 0:
            out[str(case_id)] = taken
    return out


def partition(cases: List[Dict[str, Any]], shards: int,
              timings: Dict[str, float] | None = None) -> List[List[Dict[str, Any]]]:
    """Split the universe across shards without dropping or duplicating a case.

    Partitioning is how the gate stays inside its budget if the full 395 cases
    do not. Reducing the case set would be the other way, and it is the one
    thing this gate exists to avoid - a smaller universe chosen to fit the clock
    is the "current count as the test set" error wearing a different hat.

    Round-robin split the count evenly and the clock unevenly: four shards
    measured 414s, 448s, 572s and 639s, and the gate is only as quick as its
    slowest shard, so a quarter of the wall time was spent waiting. Cases are
    not equally expensive, so with measurements in hand they are packed
    longest-first into whichever shard is currently lightest. Without
    measurements the behaviour is exactly as before.
    """
    shards = max(1, int(shards))
    ordered = sorted(cases, key=lambda c: str(c.get("id")))
    timings = timings if timings is not None else load_timings()
    buckets: List[List[Dict[str, Any]]] = [[] for _ in range(shards)]
    if not timings:
        for i, case in enumerate(ordered):
            buckets[i % shards].append(case)
        return buckets

    # A case we have never timed gets the median rather than zero, so a newly
    # added case is not treated as free and piled onto one shard.
    known = sorted(timings.values())
    default = known[len(known) // 2] if known else 1.0
    loads = [0.0] * shards
    # Ties broken on id so the partition is reproducible; two runs of the same
    # commit must shard identically or the coverage check becomes a coin toss.
    for case in sorted(ordered,
                       key=lambda c: (-timings.get(str(c.get("id")), default),
                                      str(c.get("id")))):
        target = min(range(shards), key=lambda i: (loads[i], i))
        buckets[target].append(case)
        loads[target] += timings.get(str(case.get("id")), default)
    return buckets


def merge_case_seconds(reports: List[Dict[str, Any]]) -> Dict[str, float]:
    """One timings map from every shard, for the next run to shard on."""
    merged: Dict[str, float] = {}
    for report in reports:
        for case_id, value in (report.get("case_seconds") or {}).items():
            try:
                merged[str(case_id)] = round(float(value), 3)
            except (TypeError, ValueError):
                continue
    return merged


def verify_partition(cases: List[Dict[str, Any]],
                     buckets: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """The shards, recombined, must be exactly the manifest.

    Asserted rather than trusted: a partition that silently drops a shard
    reports zero defects for every case in it.
    """
    expected = manifest(cases)
    seen: List[str] = []
    for bucket in buckets:
        seen.extend(str(c.get("id")) for c in bucket)
    combined = sorted(seen)
    duplicates = len(seen) - len(set(seen))
    missing = sorted(set(expected) - set(seen))
    extra = sorted(set(seen) - set(expected))
    return {
        "matches_manifest": combined == expected and not duplicates,
        "expected_cases": len(expected),
        "combined_cases": len(seen),
        "duplicates": duplicates,
        "missing": missing[:20],
        "extra": extra[:20],
    }

def artifact_name(shard_index: int) -> str:
    return f"short_gate_zero_defect_shard_{shard_index}.json"


def namesake_manifest_ids() -> List[str]:
    from ask_product_test.company_metadata_routing_acceptance_v1 import FALLTHROUGH_CASES

    return [f"NAMESAKE-{i:03d}" for i, _ in enumerate(FALLTHROUGH_CASES, 1)]


def shard_config() -> tuple[int, int]:
    """Validated zero-based shard coordinates from the report-only workflow."""
    count = int(os.environ.get("SHORT_GATE_SHARD_COUNT") or "1")
    index = int(os.environ.get("SHORT_GATE_SHARD_INDEX") or "0")
    if count < 1 or index < 0 or index >= count:
        raise ValueError(f"invalid shard {index}/{count}")
    return count, index


def normalise_namesake_results(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep the complete ambiguous-name universe and expose wrong bindings.

    These cases intentionally carry no ticker, so selecting identity-bearing
    core cases excludes the two historical `bound_namesake` failures. Coverage
    is proven against FALLTHROUGH_CASES before any result is accepted.
    """
    from ask_product_test.company_metadata_routing_acceptance_v1 import FALLTHROUGH_CASES

    by_question = {str(r.get("question")): r for r in rows
                   if r.get("kind") == "fallthrough"}
    expected = list(FALLTHROUGH_CASES)
    if set(by_question) != set(expected):
        missing = sorted(set(expected) - set(by_question))
        extra = sorted(set(by_question) - set(expected))
        raise RuntimeError(
            f"namesake universe mismatch: missing={missing} extra={extra}")

    out: List[Dict[str, Any]] = []
    for i, question in enumerate(expected, 1):
        row = by_question[question]
        labels = list(row.get("failed") or [])
        bound_wrong = any(str(label).startswith("bound_namesake") for label in labels)
        out.append({
            **row,
            "id": f"NAMESAKE-{i:03d}",
            "section": "company_metadata_namesake_fallthrough",
            "flags": {"wrong_entity": bound_wrong},
            "failed": labels,
        })
    return out


def load_namesake_results() -> List[Dict[str, Any]]:
    """Run the routing suite and extract every ambiguous-name fallthrough case.

    ``evaluate_pipeline`` covers only twelve positive metadata questions. The
    complete fallthrough universe lives in ``evaluate``; using the former makes
    all six namesake cases disappear and must be treated as infrastructure.
    """
    from ask_product_test.company_metadata_routing_acceptance_v1 import evaluate

    report = evaluate()
    return normalise_namesake_results(list(report.get("results") or []))


def _load_stub():
    """Install the deterministic provider into the real pipeline.

    Its absence is infrastructure, not a result. A required lane that downgrades
    to NOT_RUN when its determinism source is missing reports nothing while
    looking like it found nothing. The separate grounded-synthesis model must
    also stay off: it is a final prose layer, not routing or identity logic, and
    allowing it here makes a required check depend on network retries.
    """
    from ask_product_test import provider_stub

    # Enforce this in the runner, not only in workflow YAML. Repository or host
    # credentials can otherwise make the same commit exercise a live model in
    # one environment and deterministic synthesis in another.
    os.environ["ASK_LLM_ENABLED"] = "false"
    os.environ["YAHOO_PROVIDER"] = "false"
    os.environ["YAHOO_YFINANCE_FALLBACK"] = "false"

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
                 cases_planned: int, stub_ok: bool,
                 manifest_ids: List[str] | None = None,
                 shard_index: int = 0, shard_count: int = 1,
                 case_seconds: Dict[str, float] | None = None) -> Dict[str, Any]:
    """Counters, unique failing cases, and categories - kept apart."""
    defects = zde.summarise(results, defects=zde.REQUIRED_DEFECTS, provider_ok=stub_ok)
    categories = tax.classify(results)

    # A case can carry several labels. Counting labels as cases overstates the
    # problem; counting cases as labels hides which problems are present. Both
    # are reported, and neither is derived from the other.
    failing_cases = {str(r.get("id")) for r in results if r.get("failed")}
    p0_cases = {str(r.get("id")) for r in results
                if any(tax.categorise(l) in tax.RELEASE_CRITICAL
                       for l in (r.get("failed") or []))}
    evaluated_ids = sorted(str(r.get("id")) for r in results)
    expected_ids = sorted(manifest_ids or evaluated_ids)

    non_p0 = {c: n for c, n in categories["by_category"].items()
              if c not in tax.RELEASE_CRITICAL}

    return {
        "suite": "short_gate_zero_defect",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_only": False,
        "blocks_merge": True,
        "blocks_deployment": True,
        "required_check": True,
        "section_mapping": "PROVISIONAL — awaiting product owner approval",
        "provider": "deterministic stub",
        "shard_index": shard_index,
        "shard_count": shard_count,
        "cases_planned": cases_planned,
        "cases_evaluated": len(results),
        "manifest_case_ids": expected_ids,
        "evaluated_case_ids": evaluated_ids,
        "elapsed_seconds": round(elapsed, 1),
        "budget_seconds": budget_seconds(),
        "within_budget": elapsed <= budget_seconds(),
        # Feeds the next run's partition; see load_timings.
        "case_seconds": case_seconds or {},
        # unique cases, held separately from label counts
        "unique_failing_cases": len(failing_cases),
        "failing_case_ids": sorted(failing_cases),
        "unique_p0_cases": len(p0_cases),
        "p0_case_ids": sorted(p0_cases),
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


def combine_reports(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine shards only when they prove exact manifest coverage."""
    if not reports:
        raise ValueError("no shard reports")
    shard_count = int(reports[0].get("shard_count") or 0)
    if shard_count < 1 or len(reports) != shard_count:
        raise ValueError(f"expected {shard_count} shard reports, found {len(reports)}")
    indexes = [int(r.get("shard_index", -1)) for r in reports]
    if sorted(indexes) != list(range(shard_count)):
        raise ValueError(f"shard indexes are incomplete or duplicated: {indexes}")

    expected = list(reports[0].get("manifest_case_ids") or [])
    for report in reports[1:]:
        if list(report.get("manifest_case_ids") or []) != expected:
            raise ValueError("shards disagree on the extraction manifest")

    seen = [case_id for report in reports
            for case_id in (report.get("evaluated_case_ids") or [])]
    duplicates = len(seen) - len(set(seen))
    missing = sorted(set(expected) - set(seen))
    extra = sorted(set(seen) - set(expected))
    if duplicates or missing or extra or sorted(seen) != sorted(expected):
        raise ValueError(
            f"shard coverage mismatch: duplicates={duplicates} "
            f"missing={missing[:20]} extra={extra[:20]}")

    defect_keys = {key for report in reports for key in (report.get("defects") or {})}
    defects = {key: sum(int((r.get("defects") or {}).get(key) or 0) for r in reports)
               for key in sorted(defect_keys)}
    categories: Counter[str] = Counter()
    for report in reports:
        categories.update({k: int(v) for k, v in (report.get("by_category") or {}).items()})
    failing_ids = sorted({case_id for report in reports
                          for case_id in (report.get("failing_case_ids") or [])})
    p0_ids = sorted({case_id for report in reports
                     for case_id in (report.get("p0_case_ids") or [])})
    max_elapsed = max(float(r.get("elapsed_seconds") or 0) for r in reports)
    budget = min(int(r.get("budget_seconds") or BUDGET_SECONDS) for r in reports)
    return {
        "suite": "short_gate_zero_defect_combined",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_only": False,
        "blocks_merge": True,
        "blocks_deployment": True,
        "required_check": True,
        "shard_count": shard_count,
        "cases_planned": len(expected),
        "cases_evaluated": len(seen),
        "manifest_case_ids": expected,
        "coverage_complete": True,
        "duplicates": 0,
        "elapsed_seconds": round(max_elapsed, 1),
        "budget_seconds": budget,
        "within_budget": max_elapsed <= budget,
        "defects": defects,
        "zero_defect": all(value == 0 for value in defects.values()),
        "unique_failing_cases": len(failing_ids),
        "failing_case_ids": failing_ids,
        "unique_p0_cases": len(p0_ids),
        "p0_case_ids": p0_ids,
        "label_occurrences": sum(int(r.get("label_occurrences") or 0) for r in reports),
        "by_category": dict(sorted(categories.items())),
        "decision": "PASS" if all(value == 0 for value in defects.values()) else "FAIL",
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
    try:
        shard_count, shard_index = shard_config()
    except (TypeError, ValueError) as exc:
        print(f"[short_gate] INFRASTRUCTURE: {exc}", flush=True)
        return EXIT_INFRASTRUCTURE
    timings = load_timings()
    selected_cases = partition(cases, shard_count, timings)[shard_index]
    known = sum(1 for c in cases if str(c.get("id")) in timings)
    print(f"[short_gate] partition: "
          + (f"balanced on {known}/{len(cases)} timed cases"
             if timings else "round-robin (no timings file yet)"), flush=True)
    full_manifest = sorted(manifest(cases) + namesake_manifest_ids())
    print(f"[short_gate] shard {shard_index + 1}/{shard_count}: "
          f"{len(selected_cases)} of {len(cases)} core cases — every J_impossible and every "
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
    # Timed per case so the next run can pack the shards by cost instead of by
    # count. Wall clock around the whole case, because that is what a shard
    # actually pays.
    case_seconds: Dict[str, float] = {}
    for i, case in enumerate(selected_cases, 1):
        started = time.perf_counter()
        transport = harness.ask(
            case["question"], ticker=case.get("ticker"), case=case
        )
        payload = transport.get("payload") if isinstance(transport.get("payload"), dict) else {}
        results.append(evaluate_case(case, payload, int(transport.get("latency_ms") or 0)))
        case_seconds[str(case.get("id"))] = round(time.perf_counter() - started, 3)
        if i % 50 == 0:
            print(f"  … {i}/{len(selected_cases)}  ({time.perf_counter()-t0:.0f}s)", flush=True)

    namesake_results: List[Dict[str, Any]] = []
    if shard_index == 0:
        try:
            namesake_results = load_namesake_results()
        except Exception as exc:
            print(f"[short_gate] INFRASTRUCTURE: namesake universe could not be "
                  f"verified: {type(exc).__name__}: {exc}", flush=True)
            return EXIT_INFRASTRUCTURE
        print(f"[short_gate] {len(namesake_results)} ambiguous-name fallthrough "
              f"cases — none may bind a namesake", flush=True)
    results.extend(namesake_results)
    elapsed = time.perf_counter() - t0

    report = build_report(results, elapsed=elapsed,
                          cases_planned=len(full_manifest), stub_ok=True,
                          manifest_ids=full_manifest,
                          shard_index=shard_index, shard_count=shard_count,
                          case_seconds=case_seconds)
    out = _artifact_dir() / artifact_name(shard_index)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n[short_gate] decision={report['decision']} "
          f"zero_defect={report['zero_defect']} "
          f"unique_failing_cases={report['unique_failing_cases']} "
          f"unique_p0_cases={report['unique_p0_cases']} "
          f"labels={report['label_occurrences']}", flush=True)
    print(f"[short_gate] defects={report['defects']}", flush=True)
    print(f"[short_gate] non-P0 (tracked, not blocking)={report['non_p0_categories']}",
          flush=True)
    print(f"[short_gate] {report['elapsed_seconds']}s of {budget_seconds()}s budget "
          f"(within={report['within_budget']})", flush=True)
    print(f"[short_gate] artifact: {out}", flush=True)
    print("[short_gate] report-only: blocks no merge and no deployment", flush=True)
    return EXIT_OK if report["zero_defect"] else EXIT_DEFECTS


if __name__ == "__main__":
    raise SystemExit(main())
