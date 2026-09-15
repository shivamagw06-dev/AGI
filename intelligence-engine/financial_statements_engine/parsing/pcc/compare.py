"""Comparison engine — parser output vs verified reference truth."""

from __future__ import annotations

from typing import Any


def _set(xs: Any) -> set[str]:
    if xs is None:
        return set()
    if isinstance(xs, dict):
        return {str(k) for k in xs.keys()}
    return {str(x) for x in xs}


def _metric_values(mapped: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (mapped or {}).items():
        if isinstance(v, dict):
            out[str(k)] = v.get("normalized_value")
            if out[str(k)] is None:
                out[str(k)] = v.get("reported_value")
        else:
            out[str(k)] = v
    return out


def compare_case(parse_result: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    """Record every difference. Never mutates parse_result or golden expected."""
    expected = case.get("expected") or {}
    exp_metrics = expected.get("metrics") or {}
    must = _set(exp_metrics.get("expected_metrics") or exp_metrics.get("must_extract"))
    must_values = exp_metrics.get("expected_values") or {}
    forbid_extra = bool(exp_metrics.get("forbid_extra_metrics", False))

    got_mapped = (parse_result.get("mapped") or {}).get("metrics") or {}
    got = _set(got_mapped)
    got_vals = _metric_values(got_mapped)

    lost = sorted(must - got)
    additional = sorted(got - must) if forbid_extra else []
    value_changes: list[dict[str, Any]] = []
    for metric, exp_val in (must_values or {}).items():
        if metric not in got_vals:
            continue
        if got_vals[metric] != exp_val:
            value_changes.append({"metric": metric, "expected": exp_val, "got": got_vals[metric]})

    tp = len(must & got)
    mapping_accuracy = 100.0 * tp / max(1, len(must)) if must else 100.0

    # Unknown labels
    exp_unknown = expected.get("unknown_labels") or {}
    exp_unk_set = _set(exp_unknown.get("expected_unknown_labels") or exp_unknown.get("labels") or [])
    allow_unknown = set(exp_unk_set)
    got_unk = _set((parse_result.get("mapped") or {}).get("unknown_fields") or {})
    unexpected_unknown = sorted(got_unk - allow_unknown)
    missing_unknown = sorted(allow_unknown - got_unk)  # expected unknowns not seen
    total_labels = len(got) + len(got_unk)
    unknown_rate = 100.0 * len(got_unk) / max(1, total_labels)

    # Coverage
    exp_cov = expected.get("coverage") or {}
    exp_statuses = dict(exp_cov.get("core_domain_statuses") or {})
    must_extract_cov = _set(exp_cov.get("must_extract") or must)
    cov_matrix = parse_result.get("coverage_matrix") or {}
    got_statuses = {
        str(s.get("domain")): str(s.get("status"))
        for s in (cov_matrix.get("sections") or [])
        if s.get("domain") in exp_statuses
    }
    status_mismatches = [
        {"domain": d, "expected": exp_statuses[d], "got": got_statuses.get(d)}
        for d in sorted(exp_statuses)
        if got_statuses.get(d) != exp_statuses[d]
    ]
    cov_missing = sorted(must_extract_cov - got)
    coverage_match = 100.0 if not status_mismatches and not cov_missing else 0.0

    # Manifest
    exp_man = expected.get("manifest") or {}
    manifest = parse_result.get("manifest") or {}
    man_required = list(exp_man.get("required_fields") or ["manifest_id", "draft_id", "document_hash", "immutable"])
    man_missing_fields = [f for f in man_required if f not in manifest]
    exp_extracted = _set(exp_man.get("metrics_extracted") or must)
    man_metric_mismatch = sorted(exp_extracted - _set(manifest.get("metrics_extracted")))
    manifest_match = 100.0 if not man_missing_fields and not man_metric_mismatch else 0.0

    # Hierarchy
    exp_hier = expected.get("hierarchy") or {}
    hier = parse_result.get("hierarchy") or {}
    expect_preserved = bool(exp_hier.get("expect_hierarchy", True))
    hierarchy_ok = (hier.get("flattening_destroys_hierarchy") is False) if expect_preserved else True
    hierarchy_pct = 100.0 if hierarchy_ok else 0.0

    # Confidence
    exp_conf = expected.get("confidence") or {}
    min_overall = float(exp_conf.get("min_overall_confidence") or 0.0)
    overall = float((parse_result.get("confidence") or {}).get("overall") or 0.0)
    confidence_ok = overall >= min_overall

    # Lineage
    exp_lin = expected.get("lineage") or {}
    require_lineage = bool(exp_lin.get("require_lineage", True))
    lineage = parse_result.get("lineage") or {}
    lineage_ok = bool(lineage.get("lineage_root_id")) if require_lineage else True

    # Validation (FSE-05 placeholder)
    exp_val = expected.get("validation") or {}
    val_mode = str(exp_val.get("status") or "deferred")
    if val_mode == "deferred":
        validation_consistency = 100.0
        validation_note = "deferred_until_fse_05"
    else:
        # Future: compare validation outcomes
        validation_consistency = 100.0
        validation_note = "expected_active_not_yet_compared"

    differences: list[dict[str, Any]] = []
    if lost:
        differences.append({"kind": "lost_metrics", "items": lost})
    if additional:
        differences.append({"kind": "additional_metrics", "items": additional})
    if value_changes:
        differences.append({"kind": "changed_metric_values", "items": value_changes})
    if status_mismatches:
        differences.append({"kind": "coverage_status_mismatch", "items": status_mismatches})
    if cov_missing:
        differences.append({"kind": "coverage_must_extract_missing", "items": cov_missing})
    if man_missing_fields or man_metric_mismatch:
        differences.append(
            {
                "kind": "manifest_mismatch",
                "missing_fields": man_missing_fields,
                "missing_metrics": man_metric_mismatch,
            }
        )
    if not hierarchy_ok:
        differences.append({"kind": "hierarchy_regression", "items": ["flattening_destroys_hierarchy"]})
    if unexpected_unknown:
        differences.append({"kind": "unexpected_unknown_labels", "items": unexpected_unknown})
    if not confidence_ok:
        differences.append(
            {"kind": "confidence_regression", "expected_min": min_overall, "got": overall}
        )
    if not lineage_ok:
        differences.append({"kind": "lineage_regression", "items": ["missing_lineage_root"]})

    passed = (
        mapping_accuracy >= 99.5
        and coverage_match >= 100.0
        and manifest_match >= 100.0
        and hierarchy_pct >= 100.0
        and unknown_rate <= 0.5
        and confidence_ok
        and lineage_ok
        and not lost
        and not value_changes
    )

    return {
        "case_id": case.get("case_id"),
        "sector": case.get("sector"),
        "ticker": (case.get("metadata") or {}).get("ticker"),
        "passed": passed,
        "scores": {
            "parse_manifest_match_pct": manifest_match,
            "coverage_matrix_match_pct": coverage_match,
            "hierarchy_preservation_pct": hierarchy_pct,
            "metric_mapping_accuracy_pct": round(mapping_accuracy, 6),
            "unknown_label_rate_pct": round(unknown_rate, 6),
            "validation_consistency_pct": validation_consistency,
            "confidence_ok": confidence_ok,
            "lineage_ok": lineage_ok,
        },
        "lost_metrics": lost,
        "additional_metrics": additional,
        "changed_metric_values": value_changes,
        "unexpected_unknown_labels": unexpected_unknown,
        "missing_expected_unknown_labels": missing_unknown,
        "differences": differences,
        "metrics_compared": len(must),
        "got_metrics": sorted(got),
        "expected_metrics": sorted(must),
        "validation_note": validation_note,
        "issues_recommendations": False,
    }
