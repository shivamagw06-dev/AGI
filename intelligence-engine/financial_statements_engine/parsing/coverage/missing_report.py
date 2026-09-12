"""Structured missing-metric report — extraction gaps only, not validation."""

from __future__ import annotations

from typing import Any


def _action_for(status: str, reason: str) -> str:
    if status == "UNSUPPORTED":
        return "Add parser capability"
    if status == "NOT_PRESENT":
        return "No action"
    if status == "PARSE_FAILED":
        return "Investigate parser failure"
    if status == "MISSING":
        return "Investigate parser"
    if status == "PARTIAL":
        return "Improve extraction completeness"
    return "Review"


def build_missing_metric_report(matrix: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for sec in matrix.get("sections") or []:
        status = str(sec.get("status") or "")
        domain = sec.get("domain")
        expected = list(sec.get("expected_metrics") or [])
        extracted = set(sec.get("extracted_metrics") or [])

        if status == "UNSUPPORTED":
            for m in expected or ["(section)"]:
                rows.append(
                    {
                        "metric": m,
                        "domain": domain,
                        "expected": True,
                        "extracted": False,
                        "reason": "Parser does not currently support this section",
                        "status": "UNSUPPORTED",
                        "action": _action_for("UNSUPPORTED", ""),
                    }
                )
            continue

        if status == "NOT_PRESENT":
            for m in expected or ["(section)"]:
                rows.append(
                    {
                        "metric": m,
                        "domain": domain,
                        "expected": False,
                        "extracted": False,
                        "reason": "Company did not report the section",
                        "status": "NOT_PRESENT",
                        "action": _action_for("NOT_PRESENT", ""),
                    }
                )
            continue

        if status in ("MISSING", "PARSE_FAILED", "PARTIAL"):
            for m in expected:
                if m in extracted:
                    continue
                reason = {
                    "MISSING": "Expected but not found",
                    "PARSE_FAILED": "Section exists but extraction failed",
                    "PARTIAL": "Partially extracted; metric missing",
                }[status]
                rows.append(
                    {
                        "metric": m,
                        "domain": domain,
                        "expected": True,
                        "extracted": False,
                        "reason": reason,
                        "status": status,
                        "action": _action_for(status, reason),
                    }
                )

    return {
        "matrix_id": matrix.get("matrix_id"),
        "ticker": matrix.get("ticker"),
        "manifest_id": matrix.get("manifest_id"),
        "n": len(rows),
        "rows": rows,
        "issues_recommendations": False,
    }
