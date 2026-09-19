"""FSE-04.2 Mission Control façades — coverage analytics (observational)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.parsing.coverage.diff import diff_coverage
from financial_statements_engine.parsing.coverage.history import list_history
from financial_statements_engine.parsing.coverage.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    QUALITY_TARGETS,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.parsing.coverage.scorecard import build_scorecard
from financial_statements_engine.parsing.coverage.store import list_matrices, load_matrix
from financial_statements_engine.parsing.quality.unknown_queue import list_queue
from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "quality_targets": QUALITY_TARGETS,
        "capabilities": [
            "evidence_coverage_matrix",
            "document_scorecard",
            "missing_metric_report",
            "unknown_label_report",
            "coverage_history",
            "coverage_difference_engine",
            "mission_control_analytics",
            "regression_alerts",
        ],
        "extends": ["FSE-04", "FSE-04.1"],
        "observational_only": True,
        "blocks_publication": False,
        "validates_accounting": False,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_04_2_EVIDENCE_COVERAGE_MATRIX.md",
        "as_of": now_iso(),
    }


def _iter_all_matrices() -> list[dict[str, Any]]:
    root = ensure_dirs() / "parsing" / "coverage" / "matrices"
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for ticker_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        out.extend(list_matrices(ticker_dir.name))
    return out


def dashboard() -> dict[str, Any]:
    matrices = _iter_all_matrices()
    scorecards = [build_scorecard(m) for m in matrices]
    overall = (
        sum(float(s.get("coverage_percentage") or 0.0) for s in scorecards) / len(scorecards)
        if scorecards
        else 0.0
    )
    by_parser: dict[str, list[float]] = defaultdict(list)
    by_company: dict[str, list[float]] = defaultdict(list)
    by_doc_type: dict[str, list[float]] = defaultdict(list)
    unsupported: dict[str, int] = defaultdict(int)
    regressions = 0
    for m, sc in zip(matrices, scorecards):
        key = f"{m.get('parser_name')}@{m.get('parser_version')}"
        by_parser[key].append(float(sc["coverage_percentage"]))
        by_company[str(m.get("ticker"))].append(float(sc["coverage_percentage"]))
        by_doc_type[str(m.get("document_type"))].append(float(sc["coverage_percentage"]))
        for d in sc.get("unsupported_sections") or []:
            unsupported[str(d)] += 1

    events = [
        e
        for e in get_bus().tail(300)
        if "coverage." in str(e.get("event_type"))
    ]
    regressions = sum(1 for e in events if e.get("event_type") == "coverage.regression.detected.v1")

    def _avg(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 6) if vals else 0.0

    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "overall_coverage": round(overall, 6),
        "matrices_indexed": len(matrices),
        "coverage_by_parser": {k: _avg(v) for k, v in sorted(by_parser.items())},
        "coverage_by_company": {k: _avg(v) for k, v in sorted(by_company.items())},
        "coverage_by_statement_type": {k: _avg(v) for k, v in sorted(by_doc_type.items())},
        "unsupported_sections": dict(sorted(unsupported.items())),
        "unknown_label_queue_open": len(list_queue(status="open")),
        "coverage_regression_alerts": regressions,
        "quality_targets": QUALITY_TARGETS,
        "recent_coverage_events": events[-30:],
        "informational_only": True,
        "blocks_publication": False,
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def matrices_for(ticker: str) -> dict[str, Any]:
    rows = list_matrices(ticker)
    return {
        "ok": True,
        "ticker": ticker.upper().strip(),
        "n": len(rows),
        "matrices": rows,
        "issues_recommendations": False,
    }


def matrix_detail(ticker: str, matrix_id: str) -> dict[str, Any]:
    m = load_matrix(ticker, matrix_id)
    if not m:
        return {"ok": False, "error": "matrix_not_found", "ticker": ticker, "matrix_id": matrix_id}
    return {
        "ok": True,
        "matrix": m,
        "scorecard": build_scorecard(m),
        "issues_recommendations": False,
    }


def history_for(ticker: str, document_hash: str | None = None) -> dict[str, Any]:
    rows = list_history(ticker, document_hash)
    return {
        "ok": True,
        "ticker": ticker.upper().strip(),
        "document_hash": document_hash,
        "n": len(rows),
        "history": rows,
        "issues_recommendations": False,
    }


def diff_matrices(ticker: str, old_matrix_id: str, new_matrix_id: str) -> dict[str, Any]:
    old_m = load_matrix(ticker, old_matrix_id)
    new_m = load_matrix(ticker, new_matrix_id)
    if not old_m or not new_m:
        return {"ok": False, "error": "matrix_not_found"}
    report = diff_coverage(old_m, new_m, old_scorecard=build_scorecard(old_m), new_scorecard=build_scorecard(new_m))
    return {"ok": True, "diff": report, "issues_recommendations": False}


def analytics() -> dict[str, Any]:
    """Mission Control coverage analytics rollup."""
    dash = dashboard()
    return {
        "overall_coverage": dash["overall_coverage"],
        "coverage_by_parser": dash["coverage_by_parser"],
        "coverage_by_company": dash["coverage_by_company"],
        "coverage_by_filing_type": dash["coverage_by_statement_type"],
        "coverage_by_industry": {},  # populated when industry tags are present on matrices
        "unsupported_sections": dash["unsupported_sections"],
        "unknown_label_queue": list_queue(status="open")[:100],
        "coverage_trends": _coverage_trends(),
        "coverage_improvements": _improvements(),
        "coverage_regression_alerts": dash["coverage_regression_alerts"],
        "quality_targets": QUALITY_TARGETS,
        "informational_only": True,
        "blocks_publication": False,
        "as_of": now_iso(),
    }


def _coverage_trends() -> list[dict[str, Any]]:
    root = ensure_dirs() / "parsing" / "coverage" / "history"
    if not root.exists():
        return []
    points: list[dict[str, Any]] = []
    for ticker_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for row in list_history(ticker_dir.name):
            points.append(
                {
                    "ticker": row.get("ticker"),
                    "parser_version": row.get("parser_version"),
                    "coverage_percentage": row.get("coverage_percentage"),
                    "recorded_at": row.get("recorded_at"),
                }
            )
    return points[-100:]


def _improvements() -> list[dict[str, Any]]:
    """Positive coverage deltas from consecutive history entries per document."""
    root = ensure_dirs() / "parsing" / "coverage" / "history"
    if not root.exists():
        return []
    improvements: list[dict[str, Any]] = []
    for ticker_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in list_history(ticker_dir.name):
            by_doc[str(row.get("document_hash"))].append(row)
        for doc_hash, rows in by_doc.items():
            if len(rows) < 2:
                continue
            a, b = rows[-2], rows[-1]
            delta = float(b.get("coverage_percentage") or 0) - float(a.get("coverage_percentage") or 0)
            if delta > 0:
                improvements.append(
                    {
                        "ticker": ticker_dir.name,
                        "document_hash": doc_hash,
                        "from_parser": a.get("parser_version"),
                        "to_parser": b.get("parser_version"),
                        "coverage_gain": round(delta, 6),
                    }
                )
    return improvements[-50:]
