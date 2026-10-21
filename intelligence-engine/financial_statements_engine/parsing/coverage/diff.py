"""Coverage difference engine — parser certification input."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.parsing.coverage.schema import REGRESSION_ALERT_DROP


def _status_map(matrix: dict[str, Any]) -> dict[str, str]:
    return {str(s.get("domain")): str(s.get("status")) for s in (matrix.get("sections") or [])}


def _unknown_set(matrix: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for u in matrix.get("unknown_labels") or []:
        out.add(str(u))
    for s in matrix.get("sections") or []:
        for u in s.get("unknown_labels") or []:
            out.add(str(u))
    return out


def _coverage_pct(matrix: dict[str, Any], scorecard: dict[str, Any] | None = None) -> float:
    if scorecard and scorecard.get("coverage_percentage") is not None:
        return float(scorecard["coverage_percentage"])
    # Recompute lightly from sections
    expected_n = 0
    extracted_n = 0
    for s in matrix.get("sections") or []:
        if s.get("parser_support") != "supported":
            continue
        if s.get("status") in ("NOT_PRESENT", "UNSUPPORTED"):
            continue
        expected_n += len(s.get("expected_metrics") or [])
        extracted_n += len(s.get("extracted_metrics") or [])
    return (extracted_n / expected_n) if expected_n else 0.0


def diff_coverage(
    old_matrix: dict[str, Any],
    new_matrix: dict[str, Any],
    *,
    old_scorecard: dict[str, Any] | None = None,
    new_scorecard: dict[str, Any] | None = None,
    emit_events: bool = True,
) -> dict[str, Any]:
    old_st = _status_map(old_matrix)
    new_st = _status_map(new_matrix)
    all_domains = sorted(set(old_st) | set(new_st))

    new_sections = [
        d
        for d in all_domains
        if old_st.get(d) in (None, "NOT_PRESENT", "UNSUPPORTED", "MISSING")
        and new_st.get(d) in ("FOUND", "PARTIAL")
    ]
    lost_sections = [
        d
        for d in all_domains
        if old_st.get(d) in ("FOUND", "PARTIAL")
        and new_st.get(d) in ("MISSING", "NOT_PRESENT", "PARSE_FAILED", "UNSUPPORTED")
    ]

    old_cov = _coverage_pct(old_matrix, old_scorecard)
    new_cov = _coverage_pct(new_matrix, new_scorecard)
    delta = new_cov - old_cov
    coverage_gain = max(delta, 0.0)
    coverage_loss = max(-delta, 0.0)

    old_unk = _unknown_set(old_matrix)
    new_unk = _unknown_set(new_matrix)
    resolved = sorted(old_unk - new_unk)
    introduced = sorted(new_unk - old_unk)

    regression = coverage_loss >= REGRESSION_ALERT_DROP or bool(lost_sections)

    report = {
        "old_matrix_id": old_matrix.get("matrix_id"),
        "new_matrix_id": new_matrix.get("matrix_id"),
        "old_parser_version": old_matrix.get("parser_version"),
        "new_parser_version": new_matrix.get("parser_version"),
        "old_coverage": round(old_cov, 6),
        "new_coverage": round(new_cov, 6),
        "coverage_delta": round(delta, 6),
        "coverage_gain": round(coverage_gain, 6),
        "coverage_loss": round(coverage_loss, 6),
        "new_sections": new_sections,
        "lost_sections": lost_sections,
        "unknown_labels_resolved": resolved,
        "unknown_labels_introduced": introduced,
        "regression_alert": regression,
        "part_of_parser_certification": True,
        "issues_recommendations": False,
    }

    if emit_events and regression:
        publish(
            "coverage.regression.detected.v1",
            {
                "ticker": new_matrix.get("ticker"),
                "old_matrix_id": old_matrix.get("matrix_id"),
                "new_matrix_id": new_matrix.get("matrix_id"),
                "coverage_loss": report["coverage_loss"],
                "lost_sections": lost_sections,
            },
        )
    return report
