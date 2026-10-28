"""Document coverage scorecard — informational only; never blocks publication."""

from __future__ import annotations

from typing import Any


def build_scorecard(matrix: dict[str, Any]) -> dict[str, Any]:
    sections = list(matrix.get("sections") or [])
    by_status: dict[str, int] = {}
    for s in sections:
        st = str(s.get("status") or "")
        by_status[st] = by_status.get(st, 0) + 1

    # Applicable = not NOT_PRESENT and not UNSUPPORTED
    applicable = [s for s in sections if s.get("status") not in ("NOT_PRESENT", "UNSUPPORTED")]
    foundish = [s for s in applicable if s.get("status") in ("FOUND", "PARTIAL")]
    found_full = [s for s in applicable if s.get("status") == "FOUND"]

    # Metric-level coverage across supported domains with expectations
    expected_n = 0
    extracted_n = 0
    for s in sections:
        if s.get("parser_support") != "supported":
            continue
        if s.get("status") in ("NOT_PRESENT", "UNSUPPORTED"):
            continue
        exp = list(s.get("expected_metrics") or [])
        ext = list(s.get("extracted_metrics") or [])
        expected_n += len(exp)
        extracted_n += len(ext)

    coverage_pct = (extracted_n / expected_n) if expected_n else 0.0
    extraction_completeness = (len(found_full) / len(applicable)) if applicable else 0.0
    # Document completeness: reported (present/extracted) vs optional absent
    reported = [s for s in sections if s.get("status") not in ("NOT_PRESENT",)]
    document_completeness = (len(foundish) / len(reported)) if reported else 0.0

    unknown_labels: set[str] = set(str(u) for u in (matrix.get("unknown_labels") or []))
    for s in sections:
        for u in s.get("unknown_labels") or []:
            unknown_labels.add(str(u))
    metrics_extracted = list(matrix.get("metrics_extracted") or [])

    unsupported = [s["domain"] for s in sections if s.get("status") == "UNSUPPORTED"]
    conf = matrix.get("confidence") or {}
    parser_confidence = float(conf.get("overall") or 0.0)

    core_cov: dict[str, float] = {}
    for domain in ("income_statement", "balance_sheet", "cash_flow"):
        sec = next((s for s in sections if s.get("domain") == domain), None)
        if not sec:
            core_cov[domain] = 0.0
            continue
        exp = list(sec.get("expected_metrics") or [])
        ext = list(sec.get("extracted_metrics") or [])
        core_cov[domain] = (len(ext) / len(exp)) if exp else (1.0 if sec.get("status") == "FOUND" else 0.0)

    return {
        "matrix_id": matrix.get("matrix_id"),
        "ticker": matrix.get("ticker"),
        "manifest_id": matrix.get("manifest_id"),
        "coverage_percentage": round(coverage_pct, 6),
        "unknown_label_count": len(unknown_labels),
        "unsupported_sections": unsupported,
        "unsupported_section_count": len(unsupported),
        "parser_confidence": parser_confidence,
        "extraction_completeness": round(extraction_completeness, 6),
        "document_completeness": round(document_completeness, 6),
        "section_count": int(matrix.get("section_count") or len(sections)),
        "processing_time_ms": float(matrix.get("processing_time_ms") or 0.0),
        "status_counts": by_status,
        "core_coverage": core_cov,
        "metrics_extracted_count": len(metrics_extracted),
        "expected_metrics_count": expected_n,
        "extracted_expected_count": extracted_n,
        "informational_only": True,
        "blocks_publication": False,
        "issues_recommendations": False,
    }
