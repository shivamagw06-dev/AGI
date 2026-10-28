"""Aggregate IES metrics + Phase 2 exit gate."""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ies.schema import PHASE2_TARGETS, VALUATION_METRIC_TARGETS


def _pct(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return round(100.0 * num / den, 2)


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_suite: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by_suite.setdefault(r["suite"], []).append(r)

    suite_scores: dict[str, Any] = {}
    for suite, rows in by_suite.items():
        passed = sum(1 for r in rows if r.get("passed"))
        suite_scores[suite] = {
            "n": len(rows),
            "passed": passed,
            "score": _pct(passed, len(rows)),
            "avg_latency_ms": round(
                sum(r.get("elapsed_ms") or 0 for r in rows) / max(1, len(rows)), 1
            ),
            "unsupported_conclusions": sum(int(r.get("unsupported_conclusions") or 0) for r in rows),
            "editorial_violations": sum(int(r.get("editorial_violations") or 0) for r in rows),
            "wrong_entity_execution": sum(1 for r in rows if r.get("wrong_entity_execution")),
        }

    overall_passed = sum(1 for r in results if r.get("passed"))
    overall = _pct(overall_passed, len(results))

    # Framework metrics
    exec_rates = [r["execution_rate"] for r in results if r.get("execution_rate") is not None]
    avg_exec = round(100.0 * (sum(exec_rates) / len(exec_rates)), 2) if exec_rates else 0.0

    # Valuation-specific
    val_rows = by_suite.get("valuation") or []
    val_exec = [r for r in val_rows if r.get("frameworks_executed")]
    val_framework_execution = _pct(len(val_exec), len(val_rows)) if val_rows else 0.0
    val_unsupported = sum(int(r.get("unsupported_conclusions") or 0) for r in val_rows)
    val_entity_mismatch = sum(1 for r in val_rows if r.get("wrong_entity_execution"))

    # Evidence
    scores = [float(r["evidence_score"]) for r in results if r.get("evidence_score") is not None]
    coverages = [float(r["coverage"]) for r in results if r.get("coverage") is not None]
    prov_rows = [r for r in results if r.get("evidence_provenance_ok") is not None]
    prov_ok = sum(1 for r in prov_rows if r.get("evidence_provenance_ok"))

    false_positives = sum(
        1
        for r in results
        if r.get("suite") == "insufficient" and r.get("narrative_allowed") is True and not r.get("passed")
    )
    false_negatives = sum(
        1
        for r in results
        if r.get("suite") == "valuation" and not r.get("passed") and r.get("path") == "research"
    )

    metrics = {
        "overall_score": overall,
        "suite_scores": suite_scores,
        "framework": {
            "execution_rate_pct": avg_exec,
            "avg_framework_count": round(
                sum(len(r.get("frameworks_selected") or []) for r in results) / max(1, len(results)),
                2,
            ),
            "failure_rate_pct": round(100.0 - avg_exec, 2),
        },
        "evidence": {
            "avg_quality": round(sum(scores) / len(scores), 2) if scores else None,
            "avg_coverage": round(sum(coverages) / len(coverages), 4) if coverages else None,
            "provenance_pct": _pct(prov_ok, len(prov_rows)) if prov_rows else None,
        },
        "governance": {
            "unsupported_conclusions": sum(int(r.get("unsupported_conclusions") or 0) for r in results),
            "editorial_violations": sum(int(r.get("editorial_violations") or 0) for r in results),
            "wrong_entity_execution": sum(1 for r in results if r.get("wrong_entity_execution")),
            "justification_graph_valid_pct": _pct(
                sum(1 for r in results if r.get("justification_graph_valid")), len(results)
            ),
        },
        "performance": {
            "avg_latency_ms": round(
                sum(r.get("elapsed_ms") or 0 for r in results) / max(1, len(results)), 1
            ),
            "avg_latency_sec": round(
                (sum(r.get("elapsed_ms") or 0 for r in results) / max(1, len(results))) / 1000.0,
                3,
            ),
        },
        "valuation_detail": {
            "framework_execution_pct": val_framework_execution,
            "unsupported_valuation_claims": val_unsupported,
            "entity_mismatch": val_entity_mismatch,
            "targets": VALUATION_METRIC_TARGETS,
        },
        "errors": {
            "false_positives_pct": _pct(false_positives, max(1, len(by_suite.get("insufficient") or []))),
            "false_negatives_pct": _pct(false_negatives, max(1, len(val_rows))),
        },
    }

    # Phase 2 exit gate
    gate_checks = {
        "overall": overall >= PHASE2_TARGETS["overall"],
        "valuation": (suite_scores.get("valuation") or {}).get("score", 0) >= PHASE2_TARGETS["valuation"],
        "business_quality": (suite_scores.get("business_quality") or {}).get("score", 0)
        >= PHASE2_TARGETS["business_quality"],
        "accounting": (suite_scores.get("accounting") or {}).get("score", 0) >= PHASE2_TARGETS["accounting"],
        "comparison": (suite_scores.get("comparison") or {}).get("score", 0) >= PHASE2_TARGETS["comparison"],
        "insufficient": (suite_scores.get("insufficient") or {}).get("score", 0)
        >= PHASE2_TARGETS["insufficient"],
        "unsupported_conclusions": metrics["governance"]["unsupported_conclusions"]
        <= PHASE2_TARGETS["unsupported_conclusions"],
        "editorial_violations": metrics["governance"]["editorial_violations"]
        <= PHASE2_TARGETS["editorial_violations"],
        "wrong_entity_execution": metrics["governance"]["wrong_entity_execution"]
        <= PHASE2_TARGETS["wrong_entity_execution"],
        "framework_execution_success": avg_exec >= PHASE2_TARGETS["framework_execution_success"]
        or val_framework_execution >= PHASE2_TARGETS["framework_execution_success"],
        "justification_graphs_valid": metrics["governance"]["justification_graph_valid_pct"] >= 100.0,
    }
    if metrics["evidence"]["provenance_pct"] is not None:
        gate_checks["evidence_provenance"] = (
            metrics["evidence"]["provenance_pct"] >= PHASE2_TARGETS["evidence_provenance"]
        )

    metrics["phase2_targets"] = PHASE2_TARGETS
    metrics["phase2_gate"] = {
        "checks": gate_checks,
        "passed": all(gate_checks.values()),
        "failed": [k for k, v in gate_checks.items() if not v],
    }
    return metrics


def render_dashboard(metrics: dict[str, Any], *, version: str) -> str:
    suites = metrics.get("suite_scores") or {}
    gov = metrics.get("governance") or {}
    ev = metrics.get("evidence") or {}
    perf = metrics.get("performance") or {}
    fw = metrics.get("framework") or {}
    err = metrics.get("errors") or {}
    gate = metrics.get("phase2_gate") or {}
    lines = [
        "Institutional Evaluation Suite",
        "",
        f"Overall Score",
        "",
        f"{metrics.get('overall_score')}%",
        "",
        "Framework Execution",
        "",
        f"{(metrics.get('valuation_detail') or {}).get('framework_execution_pct', fw.get('execution_rate_pct'))}%",
        "",
        f"Evidence Coverage",
        "",
        f"{round((ev.get('avg_coverage') or 0) * 100, 1)}%",
        "",
        f"Editorial Violations",
        "",
        f"{gov.get('editorial_violations')}",
        "",
        f"Unsupported Conclusions",
        "",
        f"{gov.get('unsupported_conclusions')}",
        "",
        f"False Positives",
        "",
        f"{err.get('false_positives_pct')}%",
        "",
        f"False Negatives",
        "",
        f"{err.get('false_negatives_pct')}%",
        "",
        f"Average Evidence Quality",
        "",
        f"{ev.get('avg_quality')}",
        "",
        f"Average Latency",
        "",
        f"{perf.get('avg_latency_sec')} sec",
        "",
        "--- Suite Scores ---",
    ]
    for name, row in suites.items():
        lines.append(f"{name}: {row.get('score')}% ({row.get('passed')}/{row.get('n')})")
    lines.append("")
    lines.append(f"Phase 2 Exit Gate: {'PASS' if gate.get('passed') else 'FAIL'}")
    if gate.get("failed"):
        lines.append(f"Failed checks: {', '.join(gate['failed'])}")
    lines.append(f"IES version: {version}")
    return "\n".join(lines)
