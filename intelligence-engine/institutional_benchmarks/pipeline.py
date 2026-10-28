"""IBS pipeline: raw evidence → graph → FIRE → report → evaluate (+ consistency / blind)."""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional, Sequence

from institutional_benchmarks.catalog import get_case
from institutional_benchmarks.consistency import evaluate_consistency
from institutional_benchmarks.corpus import get_corpus
from institutional_benchmarks.quality import run_quality_checks
from institutional_benchmarks.report import assemble_report
from institutional_benchmarks.schema import IBS_SPEC, IBS_VERSION, IBS_WORKSTREAM_ID
from institutional_benchmarks.scoring import score_benchmark
from institutional_benchmarks import store as ibs_store


def _run_modules(corpus: Mapping[str, Any]) -> dict[str, Any]:
    from institutional_stress_tests.evidence_graph import build_evidence_graph
    from institutional_stress_tests.fire_from_raw import run_fire_from_raw

    graph = build_evidence_graph(corpus)
    modules = run_fire_from_raw(corpus)
    return {"graph": graph, "modules": modules}


def run_benchmark(
    case_id: str,
    *,
    cutoff: Optional[str] = None,
    fixture_answers: Optional[Mapping[str, Any]] = None,
    consistency: bool = True,
    related_questions: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    case = get_case(case_id, cutoff=cutoff)
    corpus = case["corpus"]
    pack = _run_modules(corpus)
    graph = pack["graph"]
    modules = pack["modules"]
    report = assemble_report(corpus, graph, modules)

    fixture_used = fixture_answers is not None
    if fixture_used:
        report = {**report, "fixture_answers_used": True}

    quality = run_quality_checks(report, corpus, fixture_answers_used=fixture_used)
    score = score_benchmark(report, quality, modules)

    # Consistency: re-assemble with question overlays (same corpus — no new facts)
    related_runs = []
    questions = list(related_questions or case.get("related_questions") or [])
    if consistency and questions:
        for q in questions[:3]:
            # Same report structure; annotate question — still must satisfy peer/counter rules
            rel_report = {**report, "related_question": q}
            related_runs.append({"question": q, "report": rel_report})
    consistency_result = evaluate_consistency(report, related_runs) if consistency else {"ok": True, "failure_codes": []}
    if not consistency_result.get("ok"):
        # Merge consistency failures into score
        codes = list(score.get("failure_codes") or [])
        for c in consistency_result.get("failure_codes") or []:
            if c not in codes:
                codes.append(c)
        score = {
            **score,
            "failure_codes": codes,
            "passed": False,
            "summary": f"FAIL — consistency; codes={codes}",
            "consistency": consistency_result,
        }
        quality = {
            **quality,
            "failure_codes": sorted(set(list(quality.get("failure_codes") or []) + codes)),
            "ok": False,
        }

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    result = {
        "ok": True,
        "workstream_id": IBS_WORKSTREAM_ID,
        "version": IBS_VERSION,
        "spec": IBS_SPEC,
        "case_id": case.get("case_id"),
        "title": case.get("title"),
        "company": case.get("company"),
        "sector": case.get("sector"),
        "time_window": case.get("time_window"),
        "historical_cutoff": cutoff or corpus.get("historical_cutoff"),
        "raw_evidence_only": True,
        "fixture_answers_used": fixture_used,
        "institutional_report": report,
        "evidence_matrix": report.get("evidence_matrix"),
        "research_quality_score": score.get("weighted_total"),
        "score": score,
        "failure_codes": score.get("failure_codes"),
        "quality": quality,
        "consistency": consistency_result,
        "coverage_summary": {
            "document_count": corpus.get("document_count"),
            "evidence_types": graph.get("coverage_by_type"),
            "citation_coverage": quality.get("citation_coverage"),
            "modules_ok": [k for k, v in modules.items() if not k.startswith("_") and v.get("ok")],
            "hidden_after_cutoff": corpus.get("hidden_after_cutoff"),
        },
        "confidence_summary": (report.get("sections") or {}).get("confidence_discussion") or {},
        "passed": bool(score.get("passed")),
        "processing_ms": elapsed_ms,
    }
    ibs_store.record(result)
    return result


def run_sector(sector: str, **kwargs: Any) -> dict[str, Any]:
    from institutional_benchmarks.catalog import list_cases

    rows = list_cases(sector=sector)
    results = [run_benchmark(r["case_id"], **kwargs) for r in rows]
    return _aggregate(results, label=f"sector:{sector}")


def run_all(**kwargs: Any) -> dict[str, Any]:
    from institutional_benchmarks.catalog import list_cases

    rows = list_cases()
    results = [run_benchmark(r["case_id"], **kwargs) for r in rows]
    return _aggregate(results, label="all")


def _aggregate(results: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    scores = [float(r.get("research_quality_score") or 0.0) for r in results]
    passed = sum(1 for r in results if r.get("passed"))
    failed = len(results) - passed
    avg = round(sum(scores) / max(1, len(scores)), 2)
    hall = sum(int((r.get("quality") or {}).get("hallucination_count") or 0) for r in results)
    prov = sum(int((r.get("quality") or {}).get("broken_provenance_count") or 0) for r in results)
    unsup = sum(int((r.get("quality") or {}).get("unsupported_count") or 0) for r in results)
    cons = sum(1 for r in results if "CONSISTENCY_FAILURE" in (r.get("failure_codes") or []))
    out = {
        "ok": True,
        "label": label,
        "workstream_id": IBS_WORKSTREAM_ID,
        "cases_run": len(results),
        "passed": passed,
        "failed": failed,
        "average_score": avg,
        "hallucination_count": hall,
        "broken_provenance": prov,
        "unsupported_conclusions": unsup,
        "consistency_failures": cons,
        "results": [
            {
                "case_id": r.get("case_id"),
                "sector": r.get("sector"),
                "passed": r.get("passed"),
                "score": r.get("research_quality_score"),
                "failure_codes": r.get("failure_codes"),
                "processing_ms": r.get("processing_ms"),
            }
            for r in results
        ],
        "release_gate": {
            "average_ok": avg >= 85.0,
            "hallucinations_ok": hall == 0,
            "provenance_ok": prov == 0,
            "unsupported_ok": unsup == 0,
            "consistency_ok": cons == 0,
            "blocked": not (avg >= 85.0 and hall == 0 and prov == 0 and unsup == 0 and cons == 0),
        },
    }
    ibs_store.record_suite(out)
    return out
