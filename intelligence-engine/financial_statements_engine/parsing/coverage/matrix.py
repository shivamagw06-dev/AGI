"""Build immutable Evidence Coverage Matrix from a successful parse."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from financial_statements_engine.parsing.coverage.domains import (
    all_domain_specs,
    normalize_section_token,
    section_present,
)
from financial_statements_engine.parsing.coverage.schema import (
    EXTRACTION_STATUSES,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.util import now_iso


def new_matrix_id() -> str:
    return f"ecm:{uuid.uuid4().hex[:20]}"


def _period_kind(period_info: dict[str, Any] | None) -> str:
    pk = str((period_info or {}).get("period_kind") or "").lower()
    if pk in ("quarter", "quarterly", "q"):
        return "quarterly"
    if pk in ("annual", "year", "yearly", "fy"):
        return "annual"
    return pk or "unknown"


def _classify_status(
    *,
    parser_support: str,
    expectation: str,
    period_kind: str,
    present: bool,
    expected: list[str],
    extracted: list[str],
    parse_errors: list[Any] | None,
    section_failed: bool,
) -> str:
    if parser_support == "unsupported":
        # Even if unsupported, extracted metrics upgrade status (observational honesty)
        if extracted:
            return "PARTIAL" if expected and set(extracted) != set(expected) else "FOUND"
        return "UNSUPPORTED"

    if section_failed or (present and parse_errors and not extracted):
        return "PARSE_FAILED"

    if expected:
        hit = [m for m in expected if m in extracted]
        if hit and len(hit) == len(expected):
            return "FOUND"
        if hit:
            return "PARTIAL"
        # Nothing extracted for this domain
        if present:
            return "PARSE_FAILED" if parse_errors else "MISSING"
        if expectation == "core":
            return "MISSING"
        if expectation == "period_quarterly" and period_kind == "quarterly":
            return "MISSING"
        if expectation == "period_annual" and period_kind == "annual":
            return "MISSING"
        return "NOT_PRESENT"

    # Narrative / empty-metric domains
    if present:
        return "PARSE_FAILED" if section_failed else "FOUND"
    return "NOT_PRESENT"


def _unknown_for_domain(domain_key: str, unknown_fields: dict[str, Any] | list[str] | None) -> list[str]:
    if not unknown_fields:
        return []
    if isinstance(unknown_fields, list):
        return sorted(str(x) for x in unknown_fields)
    # Heuristic: attach unknowns whose normalized label mentions domain aliases lightly
    # Prefer leaving unknowns at document level; section report can list all.
    out: list[str] = []
    token = normalize_section_token(domain_key)
    for label in unknown_fields.keys():
        nl = normalize_section_token(label)
        if token in nl or any(p in nl for p in token.split("_") if len(p) > 3):
            out.append(str(label))
    return sorted(out)


def build_coverage_matrix(
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
    parse_errors: list[Any] | None = None,
    page_hints: dict[str, list[int]] | None = None,
    table_counts: dict[str, int] | None = None,
    row_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Deterministic observational matrix. Never mutates financial facts."""
    if isinstance(metrics_extracted, dict):
        extracted_list = sorted(str(k) for k in metrics_extracted.keys())
        extracted_set = set(extracted_list)
    else:
        extracted_list = sorted(str(k) for k in (metrics_extracted or []))
        extracted_set = set(extracted_list)

    period_kind = _period_kind(period_info)
    conf_overall = float((confidence or {}).get("overall") or 0.0)
    sections: list[dict[str, Any]] = []

    for spec in all_domain_specs():
        key = spec["domain"]
        expected = list(spec["expected_metrics"])
        extracted_here = [m for m in expected if m in extracted_set]
        # Also credit metrics that belong to domain statement_type even if not in core expected
        # (already covered via expected list for supported domains)
        missing = [m for m in expected if m not in extracted_set]
        present = section_present(key, sections_found) or bool(extracted_here)
        status = _classify_status(
            parser_support=spec["parser_support"],
            expectation=spec["expectation"],
            period_kind=period_kind,
            present=present,
            expected=expected,
            extracted=extracted_here,
            parse_errors=parse_errors,
            section_failed=False,
        )
        assert status in EXTRACTION_STATUSES
        unknown_labels = _unknown_for_domain(key, unknown_fields)
        sections.append(
            {
                "section_name": spec["section_name"],
                "domain": key,
                "status": status,
                "expected_metrics": expected,
                "extracted_metrics": extracted_here,
                "missing_metrics": missing if status in ("MISSING", "PARTIAL", "PARSE_FAILED") else [],
                "unknown_labels": unknown_labels,
                "confidence": conf_overall if extracted_here or present else 0.0,
                "page_numbers": list((page_hints or {}).get(key) or []),
                "table_count": int((table_counts or {}).get(key) or 0),
                "row_count": int((row_counts or {}).get(key) or 0),
                "parser_version": parser_version,
                "processing_time_ms": float(processing_time_ms),
                "parser_support": spec["parser_support"],
            }
        )

    # Deterministic fingerprint excludes wall-clock / matrix_id
    if isinstance(unknown_fields, dict):
        document_unknowns = sorted(str(k) for k in unknown_fields.keys())
    elif isinstance(unknown_fields, list):
        document_unknowns = sorted(str(x) for x in unknown_fields)
    else:
        document_unknowns = []

    fingerprint_core = {
        "ticker": ticker.upper().strip(),
        "document_hash": document_hash,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "pne_version": pne_version,
        "metric_registry_version": metric_registry_version,
        "sections": [
            {
                "domain": s["domain"],
                "status": s["status"],
                "extracted_metrics": s["extracted_metrics"],
                "missing_metrics": s["missing_metrics"],
                "unknown_labels": s["unknown_labels"],
            }
            for s in sections
        ],
        "metrics_extracted": extracted_list,
        "unknown_labels": document_unknowns,
    }
    coverage_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_core, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    return {
        "matrix_id": new_matrix_id(),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "immutable": True,
        "observational_only": True,
        "validates_accounting": False,
        "modifies_financial_data": False,
        "blocks_publication": False,
        "ticker": ticker.upper().strip(),
        "company_id": company_id,
        "industry": industry,
        "evidence_id": evidence_id,
        "draft_id": draft_id,
        "manifest_id": manifest_id,
        "document_hash": document_hash,
        "document_type": document_type,
        "parser_name": parser_name,
        "parser_version": parser_version,
        "pne_version": pne_version,
        "metric_registry_version": metric_registry_version,
        "period_kind": period_kind,
        "sections_found": list(sections_found or []),
        "metrics_extracted": extracted_list,
        "unknown_labels": document_unknowns,
        "sections": sections,
        "section_count": len(sections),
        "coverage_fingerprint": coverage_fingerprint,
        "processing_time_ms": float(processing_time_ms),
        "confidence": confidence or {},
        "created_at": now_iso(),
        "issues_recommendations": False,
    }
