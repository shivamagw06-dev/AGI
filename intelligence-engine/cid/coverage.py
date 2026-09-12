"""Coverage score computation for CID."""

from __future__ import annotations

from typing import Any

from cid.schema import COVERAGE_CATEGORIES, coverage_grade


def compute_coverage(dossier: dict[str, Any]) -> dict[str, Any]:
    """Recompute per-category and overall coverage from dossier contents."""
    docs = dossier.get("documents") or {}
    counts = {
        "annual_reports": len(docs.get("annual_reports") or []),
        "quarterly_results": len(docs.get("quarterly_results") or []),
        "investor_presentations": len(docs.get("investor_presentations") or []),
        "conference_calls": len(docs.get("conference_call_transcripts") or []),
        "corporate_announcements": len(dossier.get("announcements") or []),
        "financial_statements": _fs_count(dossier),
        "market_data": 1 if _has_market_data(dossier) else 0,
        "valuation": 1 if _has_valuation(dossier) else 0,
        "sector_kpis": 1 if (dossier.get("sector_kpis") or {}).get("priority_metrics") else 0,
    }

    # Soft scores: presence → 1.0, partial conference calls scale
    coverage: dict[str, dict[str, Any]] = {}
    scores: list[float] = []
    for cat in COVERAGE_CATEGORIES:
        n = int(counts.get(cat) or 0)
        if cat == "conference_calls":
            score = min(1.0, n / 2.0) if n else 0.0  # 2+ transcripts = 100%
        elif cat in {"market_data", "valuation", "sector_kpis"}:
            score = 1.0 if n else 0.0
        else:
            score = 1.0 if n else 0.0
        coverage[cat] = {"present": score >= 1.0 or (cat == "conference_calls" and n > 0), "count": n, "score": round(score, 4)}
        scores.append(score)

    overall = sum(scores) / len(scores) if scores else 0.0
    missing = [c for c, row in coverage.items() if row["score"] < 1.0]
    return {
        "coverage": coverage,
        "coverage_score": round(overall, 4),
        "coverage_grade": coverage_grade(overall),
        "missing_evidence": missing,
        "institutional_ready": overall >= 0.90,
    }


def _fs_count(dossier: dict[str, Any]) -> int:
    fs = dossier.get("financial_statements") or {}
    n = 0
    for stmt in ("income_statement", "balance_sheet", "cash_flow"):
        block = fs.get(stmt) or {}
        n += len(block.get("annual") or []) + len(block.get("quarterly") or [])
    n += len(fs.get("versions") or [])
    # Documents of type financial_statements also count
    for bucket in ("quarterly_results", "annual_reports"):
        n += len((dossier.get("documents") or {}).get(bucket) or [])
    return n


def _has_market_data(dossier: dict[str, Any]) -> bool:
    md = dossier.get("market_data") or {}
    if md.get("current_price") is not None or md.get("market_cap") is not None:
        return True
    # Timeline / evidence with market_data type
    for e in dossier.get("evidence_timeline") or []:
        if e.get("evidence_type") == "market_data":
            return True
    return False


def _has_valuation(dossier: dict[str, Any]) -> bool:
    val = dossier.get("valuation") or {}
    if val.get("current") or val.get("preferred_methodology") or val.get("historical"):
        return True
    for e in dossier.get("evidence_timeline") or []:
        if e.get("evidence_type") == "valuation_metrics":
            return True
    return False
