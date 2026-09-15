"""Candidate freeze tooling — never auto-promotes into golden expected/."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.pcc.corpus import load_case
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def freeze_candidate(sector: str, case_id: str, parse_result: dict[str, Any]) -> dict[str, Any]:
    """Write a candidate expected pack to the runtime store only — never into golden expected/."""
    # Touch case for existence / immutability guard; do not write into corpus tree.
    case = load_case(sector, case_id)
    if case.get("immutable", True) is False:
        pass  # still never auto-promote

    store_dir = ensure_dirs() / "parsing" / "pcc" / "candidates" / sector / case_id
    store_dir.mkdir(parents=True, exist_ok=True)
    stamp = now_iso().replace(":", "").replace("-", "")[:15]
    dest = store_dir / stamp
    dest.mkdir(parents=True, exist_ok=True)

    mapped = (parse_result.get("mapped") or {}).get("metrics") or {}
    unknown = (parse_result.get("mapped") or {}).get("unknown_fields") or {}
    cov = parse_result.get("coverage_matrix") or {}
    statuses = {
        str(s.get("domain")): str(s.get("status"))
        for s in (cov.get("sections") or [])
        if s.get("domain") in ("income_statement", "balance_sheet", "cash_flow")
    }
    candidate = {
        "warning": "CANDIDATE_ONLY_NOT_REFERENCE_TRUTH",
        "auto_promote_forbidden": True,
        "sector": sector,
        "case_id": case_id,
        "metrics": {"expected_metrics": sorted(mapped.keys()), "forbid_extra_metrics": False},
        "coverage": {
            "must_extract": sorted(mapped.keys()),
            "core_domain_statuses": statuses,
        },
        "unknown_labels": {"expected_unknown_labels": sorted(unknown.keys())},
        "manifest": {
            "required_fields": ["manifest_id", "draft_id", "document_hash", "immutable"],
            "metrics_extracted": sorted(mapped.keys()),
        },
        "hierarchy": {"expect_hierarchy": True},
        "confidence": {
            "min_overall_confidence": float((parse_result.get("confidence") or {}).get("overall") or 0.0)
        },
        "lineage": {"require_lineage": True},
        "validation": {"status": "deferred"},
        "created_at": now_iso(),
        "source_manifest_id": parse_result.get("manifest_id"),
        "source_coverage_matrix_id": parse_result.get("coverage_matrix_id"),
    }
    write_json_atomic(dest / "candidate.json", candidate)

    return {
        "ok": True,
        "candidate_path": str(dest / "candidate.json"),
        "corpus_path_written": False,
        "promoted_to_expected": False,
        "message": "Candidate written to runtime store only. Manual review required before any expected/ update.",
        "issues_recommendations": False,
    }


def promote_forbidden_guard() -> dict[str, Any]:
    return {
        "auto_promote": False,
        "forbidden": True,
        "reason": "Parser output never becomes reference truth automatically (FSE-04.3)",
    }
