"""FSE-04.3 Mission Control façades for the Production Certification Corpus."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.parsing.pcc.certify import run_corpus_certification
from financial_statements_engine.parsing.pcc.corpus import corpus_health, list_cases, list_sectors
from financial_statements_engine.parsing.pcc.history import latest_certification, list_certifications, load_certification
from financial_statements_engine.parsing.pcc.schema import (
    ISSUES_RECOMMENDATIONS,
    PCC_GATES,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SECTORS,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    ch = corpus_health()
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "pcc_gates": PCC_GATES,
        "capabilities": [
            "production_certification_corpus",
            "golden_dataset",
            "comparison_engine",
            "regression_detection",
            "certification_report",
            "certification_history",
            "mission_control_dashboard",
            "sector_coverage",
        ],
        "extends": ["FSE-04", "FSE-04.1", "FSE-04.2"],
        "corpus": ch,
        "read_only_golden": True,
        "auto_promote_forbidden": True,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_04_3_PRODUCTION_CERTIFICATION_CORPUS.md",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    ch = corpus_health()
    latest = latest_certification()
    history = list_certifications(limit=50)
    failed = [h for h in history if not h.get("passed")]
    events = [e for e in get_bus().tail(300) if "pcc." in str(e.get("event_type"))]
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "certification_dashboard": {
            "latest": {
                "certification_id": (latest or {}).get("certification_id"),
                "passed": (latest or {}).get("passed"),
                "production_eligible": (latest or {}).get("production_eligible"),
                "deployment_recommendation": (latest or {}).get("deployment_recommendation"),
                "coverage_score": (latest or {}).get("coverage_score"),
            }
            if latest
            else None,
            "history_n": len(history),
            "failed_certifications": len(failed),
        },
        "golden_dataset_health": ch,
        "sector_coverage": {
            "declared": list(SECTORS),
            "present": list_sectors(),
            "cases_by_sector": ch.get("cases_by_sector"),
        },
        "recent_pcc_events": events[-30:],
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def analytics() -> dict[str, Any]:
    history = list_certifications(limit=200)
    cases = list_cases()
    parser_board: dict[str, list[bool]] = defaultdict(list)
    coverage_board: dict[str, list[float]] = defaultdict(list)
    for h in history:
        full = load_certification(str(h["certification_id"]))
        if not full:
            continue
        pv = str(full.get("parser_version") or "unknown")
        parser_board[pv].append(bool(full.get("passed")))
        coverage_board[pv].append(float(full.get("coverage_score") or 0.0))

    return {
        "certification_history": history,
        "parser_leaderboard": {
            k: {
                "runs": len(v),
                "pass_rate": round(sum(1 for x in v if x) / len(v), 6) if v else 0.0,
            }
            for k, v in sorted(parser_board.items())
        },
        "coverage_leaderboard": {
            k: round(sum(v) / len(v), 6) if v else 0.0 for k, v in sorted(coverage_board.items())
        },
        "regression_trends": [
            {
                "certification_id": h.get("certification_id"),
                "passed": h.get("passed"),
                "execution_timestamp": h.get("execution_timestamp"),
            }
            for h in history
        ],
        "sector_coverage": corpus_health().get("cases_by_sector"),
        "golden_dataset_health": corpus_health(),
        "failed_certifications": [h for h in history if not h.get("passed")],
        "pending_reviews": [c for c in cases if not c.get("verified")],
        "historical_performance": history,
        "as_of": now_iso(),
    }


def run_certification(*, sector: str | None = None) -> dict[str, Any]:
    return run_corpus_certification(sector=sector)


def history(limit: int = 50) -> dict[str, Any]:
    rows = list_certifications(limit=limit)
    return {"ok": True, "n": len(rows), "certifications": rows, "issues_recommendations": False}


def certification_detail(certification_id: str) -> dict[str, Any]:
    row = load_certification(certification_id)
    if not row:
        return {"ok": False, "error": "certification_not_found", "certification_id": certification_id}
    return {"ok": True, "certification": row, "issues_recommendations": False}


def cases(*, sector: str | None = None) -> dict[str, Any]:
    rows = list_cases(sector=sector)
    return {"ok": True, "n": len(rows), "cases": rows, "issues_recommendations": False}
