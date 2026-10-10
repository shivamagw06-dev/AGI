"""Assemble Evidence Coverage Matrix artifacts for a successful parse."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.parsing.coverage.diff import diff_coverage
from financial_statements_engine.parsing.coverage.history import append_history, list_history
from financial_statements_engine.parsing.coverage.matrix import build_coverage_matrix
from financial_statements_engine.parsing.coverage.missing_report import build_missing_metric_report
from financial_statements_engine.parsing.coverage.scorecard import build_scorecard
from financial_statements_engine.parsing.coverage.store import load_matrix, store_bundle
from financial_statements_engine.parsing.coverage.unknown_report import build_unknown_label_report


def assemble_coverage(
    *,
    ticker: str,
    company_id: str,
    evidence_id: str,
    draft_id: str,
    manifest_id: str,
    document_hash: str,
    document_type: str,
    parser_name: str,
    parser_version: str,
    pne_version: str,
    metric_registry_version: str,
    processing_time_ms: float,
    sections_found: list[str] | None,
    metrics_extracted: list[str] | dict[str, Any] | None,
    unknown_fields: dict[str, Any] | list[str] | None,
    confidence: dict[str, Any] | None,
    period_info: dict[str, Any] | None = None,
    industry: str | None = None,
    queued_unknowns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    matrix = build_coverage_matrix(
        ticker=ticker,
        company_id=company_id,
        evidence_id=evidence_id,
        draft_id=draft_id,
        manifest_id=manifest_id,
        document_hash=document_hash,
        document_type=document_type,
        parser_name=parser_name,
        parser_version=parser_version,
        pne_version=pne_version,
        metric_registry_version=metric_registry_version,
        processing_time_ms=processing_time_ms,
        sections_found=sections_found,
        metrics_extracted=metrics_extracted,
        unknown_fields=unknown_fields,
        confidence=confidence,
        period_info=period_info,
        industry=industry,
    )
    scorecard = build_scorecard(matrix)
    missing = build_missing_metric_report(matrix)
    unknown = build_unknown_label_report(matrix, unknown_fields=unknown_fields, queued=queued_unknowns)

    # Diff against prior history entry for same document (parser version changes)
    prior_entry = None
    hist = list_history(ticker, document_hash)
    if hist:
        prior_entry = hist[-1]
    coverage_diff = None
    if prior_entry and prior_entry.get("matrix_id"):
        prior_matrix = load_matrix(ticker, str(prior_entry["matrix_id"]))
        if prior_matrix:
            coverage_diff = diff_coverage(
                prior_matrix,
                matrix,
                old_scorecard={"coverage_percentage": prior_entry.get("coverage_percentage")},
                new_scorecard=scorecard,
            )

    path = store_bundle(
        matrix=matrix,
        scorecard=scorecard,
        missing_report=missing,
        unknown_report=unknown,
    )
    history_entry = append_history(
        ticker=ticker,
        document_hash=document_hash,
        matrix=matrix,
        scorecard=scorecard,
    )

    publish(
        "coverage.matrix.created.v1",
        {
            "matrix_id": matrix["matrix_id"],
            "manifest_id": manifest_id,
            "draft_id": draft_id,
            "ticker": ticker,
            "document_hash": document_hash,
            "coverage_percentage": scorecard["coverage_percentage"],
            "coverage_fingerprint": matrix["coverage_fingerprint"],
            "path": str(path),
        },
    )

    return {
        "matrix": matrix,
        "matrix_id": matrix["matrix_id"],
        "matrix_path": str(path),
        "scorecard": scorecard,
        "missing_metric_report": missing,
        "unknown_label_report": unknown,
        "history_entry": history_entry,
        "coverage_diff": coverage_diff,
        "blocks_publication": False,
        "observational_only": True,
    }
