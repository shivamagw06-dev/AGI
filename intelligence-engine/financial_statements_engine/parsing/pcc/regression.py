"""Regression detection across certification runs and case comparisons."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import publish


def detect_case_regressions(comparison: dict[str, Any]) -> list[dict[str, Any]]:
    """Map comparison differences into typed regressions with root-cause class."""
    regs: list[dict[str, Any]] = []
    ticker = comparison.get("ticker")
    case_id = comparison.get("case_id")
    sector = comparison.get("sector")

    def add(kind: str, metrics: list[Any] | None, root_cause: str) -> None:
        regs.append(
            {
                "kind": kind,
                "affected_companies": [ticker] if ticker else [],
                "affected_cases": [case_id] if case_id else [],
                "affected_sectors": [sector] if sector else [],
                "affected_metrics": list(metrics or []),
                "root_cause": root_cause,
            }
        )

    for d in comparison.get("differences") or []:
        kind = str(d.get("kind") or "")
        if kind == "lost_metrics":
            add("lost_metrics", d.get("items"), "parser_or_registry_mapping_gap")
        elif kind == "additional_metrics":
            add("additional_metrics", d.get("items"), "unexpected_extraction_or_mapping")
        elif kind == "changed_metric_values":
            add(
                "changed_metric_values",
                [x.get("metric") for x in (d.get("items") or []) if isinstance(x, dict)],
                "normalization_or_parser_value_drift",
            )
        elif kind == "coverage_status_mismatch":
            add(
                "coverage_regression",
                [x.get("domain") for x in (d.get("items") or []) if isinstance(x, dict)],
                "coverage_status_drift",
            )
        elif kind == "coverage_must_extract_missing":
            add("coverage_regression", d.get("items"), "coverage_extraction_gap")
        elif kind == "hierarchy_regression":
            add("hierarchy_changes", d.get("items"), "hierarchy_flattening")
        elif kind == "confidence_regression":
            add("confidence_regression", [], "confidence_below_floor")
        elif kind == "lineage_regression":
            add("lineage_regression", d.get("items"), "missing_lineage")
        elif kind == "manifest_mismatch":
            add("manifest_regression", d.get("missing_metrics"), "manifest_field_or_metric_drift")
        elif kind == "unexpected_unknown_labels":
            add("unknown_label_regression", d.get("items"), "new_unknown_labels")

    return regs


def detect_run_regressions(
    current_report: dict[str, Any],
    prior_report: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare aggregate certification reports across releases."""
    if not prior_report:
        return {
            "compared_to": None,
            "regressions": [],
            "regression_detection_pct": 100.0,
            "schema_regression": False,
            "metric_registry_regression": False,
        }

    regs: list[dict[str, Any]] = []
    cur_pass = set(current_report.get("passed_cases") or [])
    prior_pass = set(prior_report.get("passed_cases") or [])
    newly_failed = sorted(prior_pass - cur_pass)
    if newly_failed:
        regs.append(
            {
                "kind": "certification_case_regression",
                "affected_cases": newly_failed,
                "root_cause": "case_now_failing",
            }
        )

    cur_cov = float(current_report.get("coverage_score") or 0.0)
    prior_cov = float(prior_report.get("coverage_score") or 0.0)
    if cur_cov + 1e-9 < prior_cov:
        regs.append(
            {
                "kind": "coverage_regression",
                "prior": prior_cov,
                "current": cur_cov,
                "root_cause": "aggregate_coverage_drop",
            }
        )

    schema_reg = str(current_report.get("schema_version")) != str(prior_report.get("schema_version")) and bool(
        newly_failed
    )
    registry_reg = str(current_report.get("metric_registry_version")) != str(
        prior_report.get("metric_registry_version")
    ) and bool(newly_failed)

    if regs:
        publish(
            "pcc.regression.detected.v1",
            {
                "certification_id": current_report.get("certification_id"),
                "prior_certification_id": prior_report.get("certification_id"),
                "n": len(regs),
            },
        )

    return {
        "compared_to": prior_report.get("certification_id"),
        "regressions": regs,
        "regression_detection_pct": 100.0,
        "schema_regression": schema_reg,
        "metric_registry_regression": registry_reg,
    }
