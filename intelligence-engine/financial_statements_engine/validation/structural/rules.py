"""Structural validation rules."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.findings import extract_metrics, finding


def run(draft: dict[str, Any], *, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    metrics = extract_metrics(draft)
    period = draft.get("period") or draft.get("reporting_period") or {}
    currency = (draft.get("currency") or {}).get("canonical_currency") or (draft.get("manifest") or {}).get(
        "currency_detected"
    )
    coverage = draft.get("coverage_matrix") or {}
    sections = {str(s.get("domain")): str(s.get("status")) for s in (coverage.get("sections") or [])}

    # Period
    period_end = period.get("period_end") if isinstance(period, dict) else None
    period_kind = period.get("period_kind") if isinstance(period, dict) else None
    out.append(
        finding(
            rule_id="STR_PERIOD",
            rule_name="reporting_period_present",
            status="PASS" if period_end else "FAIL",
            severity="ERROR" if not period_end else "INFO",
            evidence={"period_end": period_end, "period_kind": period_kind},
            detail=None if period_end else "Reporting period missing",
        )
    )

    out.append(
        finding(
            rule_id="STR_CURRENCY",
            rule_name="currency_present",
            status="PASS" if currency else "FAIL",
            severity="ERROR" if not currency else "INFO",
            evidence={"currency": currency},
        )
    )

    # Units — at least one metric has scale if metrics exist
    scales = []
    for row in ((draft.get("mapped") or {}).get("metrics") or {}).values():
        if isinstance(row, dict) and (row.get("scale") or row.get("unit_scale")):
            scales.append(row.get("scale") or row.get("unit_scale"))
    units_ok = bool(scales) or not metrics
    out.append(
        finding(
            rule_id="STR_UNITS",
            rule_name="units_present",
            status="PASS" if units_ok else "WARN",
            severity="WARNING" if not units_ok else "INFO",
            evidence={"sample_scales": scales[:5]},
        )
    )

    # Required statements by coverage expectation / presence of any metrics
    for domain, keys in (
        ("income_statement", ("revenue", "net_income")),
        ("balance_sheet", ("total_assets", "total_equity")),
        ("cash_flow", ("operating_cash_flow",)),
    ):
        status = sections.get(domain)
        # If coverage says FOUND/PARTIAL/MISSING (expected), check keys
        if status in ("FOUND", "PARTIAL", "MISSING", "PARSE_FAILED") or any(k in metrics for k in keys):
            present = [k for k in keys if k in metrics]
            ok = bool(present)
            out.append(
                finding(
                    rule_id=f"STR_STMT_{domain.upper()}",
                    rule_name=f"required_statement_{domain}",
                    status="PASS" if ok else "FAIL",
                    severity="ERROR" if not ok else "INFO",
                    affected_metrics=list(keys),
                    evidence={"coverage_status": status, "present": present},
                    detail=None if ok else f"Missing core metrics for {domain}",
                )
            )
        else:
            out.append(
                finding(
                    rule_id=f"STR_STMT_{domain.upper()}",
                    rule_name=f"required_statement_{domain}",
                    status="SKIP",
                    severity="INFO",
                    evidence={"coverage_status": status},
                )
            )

    # Duplicate metrics in mapped
    mapped = (draft.get("mapped") or {}).get("metrics") or {}
    # dict keys are unique; check duplicate flags from parse
    dupes = (draft.get("duplicates") or {}).get("duplicate_flags") or []
    out.append(
        finding(
            rule_id="STR_DUP_METRICS",
            rule_name="duplicate_metrics_absent",
            status="FAIL" if dupes else "PASS",
            severity="ERROR" if dupes else "INFO",
            evidence={"duplicate_flags": dupes[:20]},
        )
    )

    # Draft identifiers
    out.append(
        finding(
            rule_id="STR_IDS",
            rule_name="statement_identifiers_valid",
            status="PASS" if draft.get("draft_id") and draft.get("evidence_id") else "FAIL",
            severity="ERROR" if not (draft.get("draft_id") and draft.get("evidence_id")) else "INFO",
            evidence={"draft_id": draft.get("draft_id"), "evidence_id": draft.get("evidence_id")},
        )
    )

    # Missing sections from coverage
    missing_sections = [d for d, st in sections.items() if st in ("MISSING", "PARSE_FAILED")]
    if missing_sections:
        out.append(
            finding(
                rule_id="STR_MISSING_SECTIONS",
                rule_name="missing_sections_reported",
                status="WARN",
                severity="WARNING",
                evidence={"missing_sections": missing_sections},
                detail="Coverage reports missing/failed sections",
            )
        )
    else:
        out.append(
            finding(
                rule_id="STR_MISSING_SECTIONS",
                rule_name="missing_sections_reported",
                status="PASS",
                severity="INFO",
            )
        )

    return out
