"""IST-02 pipeline: raw evidence → graph → FIRE → report → evaluate."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from institutional_stress_tests.evidence_graph import build_evidence_graph
from institutional_stress_tests.fire_from_raw import run_fire_from_raw
from institutional_stress_tests.quality_ist02 import run_quality_checks
from institutional_stress_tests.raw_corpus import load_corpus
from institutional_stress_tests.report_assemble_ist02 import assemble_institutional_report
from institutional_stress_tests.schema_ist02 import (
    IST02_CASE_ID,
    IST02_FREEZE_LOCKS,
    IST02_SPEC,
    IST02_VERSION,
    IST02_WORKSTREAM_ID,
)
from institutional_stress_tests.scoring_ist02 import score_ist02
from institutional_stress_tests import store as ist_store


def run_ist02(
    case_id: str = IST02_CASE_ID,
    *,
    corpus: Optional[Mapping[str, Any]] = None,
    fixture_answers: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    Execute IST-02.

    `fixture_answers` if provided triggers automatic FIXTURE_ANSWER_USED failure
    (negative test only).
    """
    raw = load_corpus(case_id, corpus=dict(corpus) if corpus else None)
    graph = build_evidence_graph(raw)
    modules = run_fire_from_raw(raw)
    report = assemble_institutional_report(raw, graph, modules)

    fixture_used = fixture_answers is not None
    if fixture_used:
        report = {**report, "fixture_answers_used": True}

    quality = run_quality_checks(report, raw, fixture_answers_used=fixture_used)
    score = score_ist02(report, quality, modules)

    coverage = {
        "document_count": raw.get("document_count") or len(raw.get("documents") or []),
        "evidence_types": (graph.get("coverage_by_type") or {}),
        "citation_coverage": quality.get("citation_coverage"),
        "modules_ok": [k for k, v in modules.items() if not k.startswith("_") and v.get("ok")],
        "graph_nodes": graph.get("node_count"),
        "graph_edges": graph.get("edge_count"),
    }
    confidence_summary = (report.get("sections") or {}).get("confidence_discussion") or {}

    result = {
        "ok": True,
        "case_id": IST02_CASE_ID,
        "workstream_id": IST02_WORKSTREAM_ID,
        "version": IST02_VERSION,
        "spec": IST02_SPEC,
        "freeze_locks": dict(IST02_FREEZE_LOCKS),
        "raw_evidence_only": True,
        "fixture_answers_used": fixture_used,
        "corpus": {
            "ticker": raw.get("ticker"),
            "document_count": coverage["document_count"],
            "event": raw.get("event"),
            "peers": raw.get("peers"),
        },
        "evidence_graph": {
            "node_count": graph.get("node_count"),
            "edge_count": graph.get("edge_count"),
            "coverage_by_type": graph.get("coverage_by_type"),
        },
        "modules": {
            k: {"ok": v.get("ok"), "source": v.get("source"), "error": v.get("error")}
            for k, v in modules.items()
            if not k.startswith("_")
        },
        "institutional_report": report,
        "evidence_matrix": report.get("evidence_matrix"),
        "research_quality_score": score.get("weighted_total"),
        "score": score,
        "failure_codes": score.get("failure_codes"),
        "coverage_summary": coverage,
        "confidence_summary": confidence_summary,
        "passed": bool(score.get("passed")),
        "quality": quality,
    }
    ist_store.record(result)
    return result
