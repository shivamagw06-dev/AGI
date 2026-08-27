"""Build immutable Validation Report."""

from __future__ import annotations

import uuid
from typing import Any

from financial_statements_engine.validation.schema import VALIDATOR_VERSION, VERSION, WORKSTREAM_ID
from financial_statements_engine.util import now_iso


def new_validation_id() -> str:
    return f"val:{uuid.uuid4().hex[:20]}"


def build_report(
    *,
    draft: dict[str, Any],
    findings: list[dict[str, Any]],
    quality: dict[str, Any],
    approval: dict[str, Any],
    processing_time_ms: float,
    schema_version: str | None = None,
) -> dict[str, Any]:
    passed = [f for f in findings if f.get("status") == "PASS"]
    failed = [f for f in findings if f.get("status") == "FAIL"]
    warnings = [f for f in findings if f.get("status") == "WARN" or f.get("severity") == "WARNING"]
    critical = [f for f in failed if f.get("severity") == "CRITICAL"]
    errors = [f for f in failed if f.get("severity") == "ERROR"]

    return {
        "validation_id": new_validation_id(),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "validator_version": VALIDATOR_VERSION,
        "draft_id": draft.get("draft_id"),
        "manifest_reference": draft.get("manifest_id"),
        "coverage_reference": draft.get("coverage_matrix_id"),
        "ticker": draft.get("ticker"),
        "document_hash": draft.get("document_hash"),
        "validation_timestamp": now_iso(),
        "schema_version": schema_version or (draft.get("manifest") or {}).get("schema_version"),
        "rules_executed": len(findings),
        "rules_passed": len(passed),
        "rules_failed": len(failed),
        "warnings": warnings,
        "errors": errors,
        "critical_errors": critical,
        "findings": findings,
        "quality_score": quality,
        "approval": approval,
        "processing_time_ms": float(processing_time_ms),
        "mutates_draft": False,
        "reparses_documents": False,
        "issues_recommendations": False,
        "immutable": True,
    }
