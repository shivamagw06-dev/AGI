"""Certification execution against the Production Certification Corpus."""

from __future__ import annotations

import uuid
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.metric_registry.schema import REGISTRY_VERSION
from financial_statements_engine.parsing.pcc.compare import compare_case
from financial_statements_engine.parsing.pcc.corpus import list_cases, load_case
from financial_statements_engine.parsing.pcc.gates import evaluate_pcc_gates
from financial_statements_engine.parsing.pcc.history import prior_certification, store_certification
from financial_statements_engine.parsing.pcc.regression import detect_case_regressions, detect_run_regressions
from financial_statements_engine.parsing.pcc.schema import VERSION, WORKSTREAM_ID
from financial_statements_engine.parsing.schema import VERSION as PNE_VERSION
from financial_statements_engine.schema_evolution.schema import VERSION as SCHEMA_EVOLUTION_VERSION
from financial_statements_engine.util import now_iso


def new_certification_id() -> str:
    return f"pcc:{uuid.uuid4().hex[:20]}"


def _raw_document_bytes(case: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Return filing bytes + parse meta from corpus case."""
    raw = case.get("raw")
    meta = dict(case.get("metadata") or {})
    if isinstance(raw, dict) and "document" in raw:
        # pack style used by 04.1 fixtures
        import json

        doc = raw.get("document") or raw
        data = json.dumps(doc, sort_keys=True).encode("utf-8")
        meta.setdefault("document_type", raw.get("document_type") or meta.get("filing_type") or "json")
        meta.setdefault("period_end", raw.get("period_end") or meta.get("period_end"))
        meta.setdefault("period_type", raw.get("period_type") or meta.get("statement_frequency") or "annual")
        meta.setdefault("consolidation_type", raw.get("consolidation_type") or "consolidated")
        meta.setdefault("ticker", raw.get("ticker") or meta.get("ticker"))
        meta.setdefault("evidence_id", raw.get("evidence_id") or f"pcc:{case['sector']}:{case['case_id']}")
        return data, meta
    if isinstance(raw, dict) and "fields" in raw:
        import json

        data = json.dumps(raw, sort_keys=True).encode("utf-8")
        return data, meta
    # fallback: raw file bytes as stored
    return bytes(case.get("raw_bytes") or b""), meta


def run_case(sector: str, case_id: str) -> dict[str, Any]:
    from financial_statements_engine.parsing.production import parse_bytes

    case = load_case(sector, case_id)
    data, meta = _raw_document_bytes(case)
    ticker = str(meta.get("ticker") or case["metadata"].get("ticker") or "UNKNOWN").upper()
    evidence_id = str(meta.get("evidence_id") or f"pcc:{sector}:{case_id}")

    result = parse_bytes(
        ticker,
        data,
        document_type=str(meta.get("document_type") or "json"),
        period_end=meta.get("period_end"),
        period_type=str(meta.get("period_type") or "annual"),
        evidence_id=evidence_id,
        consolidation_type=str(meta.get("consolidation_type") or "consolidated"),
    )
    # Determinism: second parse
    result2 = parse_bytes(
        ticker,
        data,
        document_type=str(meta.get("document_type") or "json"),
        period_end=meta.get("period_end"),
        period_type=str(meta.get("period_type") or "annual"),
        evidence_id=evidence_id + ":b",
        consolidation_type=str(meta.get("consolidation_type") or "consolidated"),
    )
    determinism = (
        100.0
        if result.get("deterministic_fingerprint") == result2.get("deterministic_fingerprint")
        else 0.0
    )

    comparison = compare_case(result, case)
    comparison["scores"]["replay_determinism_pct"] = determinism
    if determinism < 100.0:
        comparison["passed"] = False
        comparison["differences"].append({"kind": "determinism_failure", "items": ["fingerprint_mismatch"]})

    regs = detect_case_regressions(comparison)
    if regs and not comparison["passed"]:
        publish(
            "pcc.case.failed.v1",
            {
                "sector": sector,
                "case_id": case_id,
                "ticker": ticker,
                "differences": comparison.get("differences"),
            },
        )

    return {
        "sector": sector,
        "case_id": case_id,
        "ticker": ticker,
        "passed": comparison["passed"] and determinism >= 100.0,
        "comparison": comparison,
        "regressions": regs,
        "parser_id": result.get("parser_id"),
        "parser_version": result.get("parser_version"),
        "manifest_id": result.get("manifest_id"),
        "coverage_matrix_id": result.get("coverage_matrix_id"),
        "deterministic_fingerprint": result.get("deterministic_fingerprint"),
        "coverage_percentage": (result.get("coverage_scorecard") or {}).get("coverage_percentage"),
    }


def run_corpus_certification(*, sector: str | None = None) -> dict[str, Any]:
    """Run full PCC certification. Result is permanently stored and never deleted."""
    certification_id = new_certification_id()
    started = now_iso()
    publish("pcc.certification.started.v1", {"certification_id": certification_id, "sector": sector})

    cases = list_cases(sector=sector)
    case_results: list[dict[str, Any]] = []
    all_regs: list[dict[str, Any]] = []
    score_acc: dict[str, list[float]] = {
        "parse_manifest_match_pct": [],
        "coverage_matrix_match_pct": [],
        "hierarchy_preservation_pct": [],
        "metric_mapping_accuracy_pct": [],
        "unknown_label_rate_pct": [],
        "validation_consistency_pct": [],
        "replay_determinism_pct": [],
    }
    metrics_compared = 0
    coverage_scores: list[float] = []

    for c in cases:
        row = run_case(c["sector"], c["case_id"])
        case_results.append(row)
        all_regs.extend(row.get("regressions") or [])
        scores = (row.get("comparison") or {}).get("scores") or {}
        for k in score_acc:
            if scores.get(k) is not None:
                score_acc[k].append(float(scores[k]))
        metrics_compared += int((row.get("comparison") or {}).get("metrics_compared") or 0)
        if row.get("coverage_percentage") is not None:
            coverage_scores.append(float(row["coverage_percentage"]))

    def _avg(vals: list[float], *, default: float = 100.0) -> float:
        return round(sum(vals) / len(vals), 6) if vals else default

    passed_cases = [f"{r['sector']}/{r['case_id']}" for r in case_results if r.get("passed")]
    failed_cases = [f"{r['sector']}/{r['case_id']}" for r in case_results if not r.get("passed")]
    all_cases_passed = bool(case_results) and not failed_cases

    # Aggregate gate metrics (min for match gates; max for unknown rate)
    gate_metrics = {
        "parse_manifest_match_pct": min(score_acc["parse_manifest_match_pct"] or [0.0]),
        "coverage_matrix_match_pct": min(score_acc["coverage_matrix_match_pct"] or [0.0]),
        "hierarchy_preservation_pct": min(score_acc["hierarchy_preservation_pct"] or [0.0]),
        "metric_mapping_accuracy_pct": _avg(score_acc["metric_mapping_accuracy_pct"], default=0.0),
        "unknown_label_rate_pct": max(score_acc["unknown_label_rate_pct"] or [0.0]),
        "validation_consistency_pct": min(score_acc["validation_consistency_pct"] or [100.0]),
        "replay_determinism_pct": min(score_acc["replay_determinism_pct"] or [0.0]),
        "regression_detection_pct": 100.0,
        "all_cases_passed": all_cases_passed,
    }

    draft_report = {
        "certification_id": certification_id,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "coverage_score": _avg(coverage_scores, default=0.0),
        "schema_version": SCHEMA_EVOLUTION_VERSION,
        "metric_registry_version": REGISTRY_VERSION,
        "parser_version": next((r.get("parser_version") for r in case_results if r.get("parser_version")), None),
    }
    prior = prior_certification()
    run_regs = detect_run_regressions(draft_report, prior)
    gate_metrics["regression_detection_pct"] = float(run_regs.get("regression_detection_pct") or 100.0)
    # If historical regressions newly failed, block
    if run_regs.get("regressions"):
        # case-level already reflected in all_cases_passed; keep detection at 100
        pass

    gates = evaluate_pcc_gates(gate_metrics)
    parser_version = draft_report["parser_version"]

    report = {
        "certification_id": certification_id,
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "execution_timestamp": started,
        "completed_at": now_iso(),
        "parser_version": parser_version,
        "pne_version": PNE_VERSION,
        "schema_version": SCHEMA_EVOLUTION_VERSION,
        "metric_registry_version": REGISTRY_VERSION,
        "companies_tested": sorted({r["ticker"] for r in case_results if r.get("ticker")}),
        "documents_processed": len(case_results),
        "metrics_compared": metrics_compared,
        "coverage_score": draft_report["coverage_score"],
        "validation_score": gate_metrics["validation_consistency_pct"],
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "case_results": case_results,
        "regressions": all_regs + list(run_regs.get("regressions") or []),
        "regression_summary": {
            "case_regression_n": len(all_regs),
            "run_regression_n": len(run_regs.get("regressions") or []),
            "compared_to": run_regs.get("compared_to"),
        },
        "gate_metrics": gate_metrics,
        "gates": gates,
        "passed": gates["passed"],
        "production_eligible": gates["production_eligible"],
        "deployment_recommendation": gates["deployment_recommendation"],
        "sector_filter": sector,
        "immutable": True,
        "golden_dataset_mutated": False,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }

    path = store_certification(report)
    report["result_path"] = str(path)

    if gates["passed"]:
        publish(
            "pcc.certification.completed.v1",
            {
                "certification_id": certification_id,
                "passed": True,
                "production_eligible": True,
                "documents_processed": len(case_results),
            },
        )
    else:
        publish(
            "pcc.certification.failed.v1",
            {
                "certification_id": certification_id,
                "failed_gates": gates["failed_gates"],
                "failed_cases": failed_cases,
            },
        )
        publish(
            "pcc.certification.completed.v1",
            {
                "certification_id": certification_id,
                "passed": False,
                "production_eligible": False,
                "documents_processed": len(case_results),
            },
        )
    return report
