"""Aggregate scoring for Committee Certification IC-10 v2.0."""

from __future__ import annotations

from typing import Any

from committee_certification_v2.evaluate import (
    committee_verdict,
    decision_quality,
    evidence_completeness,
    financial_intelligence,
    fingerprint_row,
    governance_integrity,
    narrative_quality,
    ownership_intelligence,
    sector_differentiation,
    valuation_intelligence,
)
from committee_certification_v2.schema import AREA_WEIGHTS, GRADE_BANDS


def grade_for(score: float) -> str:
    for floor, label in GRADE_BANDS:
        if score >= floor:
            return label
    return "Not Committee Ready"


def score_company(row: dict[str, Any]) -> dict[str, Any]:
    blocks = {
        "evidence_completeness": evidence_completeness(row),
        "financial_intelligence": financial_intelligence(row),
        "ownership_intelligence": ownership_intelligence(row),
        "valuation_intelligence": valuation_intelligence(row),
        "sector_differentiation": sector_differentiation(row),
        "decision_quality": decision_quality(row),
        "narrative_quality": narrative_quality(row),
    }
    verdict = committee_verdict(blocks)
    return {
        "display": row.get("display"),
        "resolve": row.get("resolve"),
        "sector_key": row.get("sector_key"),
        "tests": blocks,
        "verdict": verdict,
        "fingerprint": fingerprint_row(row),
        "latency_ms": row.get("latency_ms"),
        "errors": row.get("errors") or [],
    }


def aggregate(company_scores: list[dict[str, Any]], *, governance: dict[str, Any]) -> dict[str, Any]:
    """Weighted suite score across companies + governance."""

    def avg(test_key: str) -> float:
        vals = [
            float(((c.get("tests") or {}).get(test_key) or {}).get("score_pct") or 0)
            for c in company_scores
        ]
        return round(sum(vals) / max(1, len(vals)), 2)

    area_pct = {
        "evidence_completeness": avg("evidence_completeness"),
        "financial_intelligence": avg("financial_intelligence"),
        "ownership_intelligence": avg("ownership_intelligence"),
        "valuation_intelligence": avg("valuation_intelligence"),
        "sector_differentiation": avg("sector_differentiation"),
        "decision_quality": avg("decision_quality"),
        "governance_integrity": float(governance.get("score_pct") or 0),
        "narrative_quality": avg("narrative_quality"),
    }

    weighted = {}
    total = 0.0
    for area, weight in AREA_WEIGHTS.items():
        pts = round(weight * (area_pct[area] / 100.0), 2)
        weighted[area] = {"weight": weight, "score_pct": area_pct[area], "points": pts}
        total += pts
    total = round(total, 2)

    verdicts: dict[str, int] = {}
    for c in company_scores:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1

    return {
        "total_score": total,
        "grade": grade_for(total),
        "areas": weighted,
        "area_pct": area_pct,
        "verdicts": verdicts,
        "governance": governance,
        "n_companies": len(company_scores),
    }


def robustness(run_fingerprints: list[dict[str, str]]) -> dict[str, Any]:
    """Compare fingerprints across consecutive runs."""
    if not run_fingerprints:
        return {"pass": False, "stable_pct": 0.0, "note": "no_runs"}
    keys = sorted(run_fingerprints[0].keys())
    stable = 0
    unstable = []
    for k in keys:
        vals = {run.get(k) for run in run_fingerprints}
        if len(vals) == 1:
            stable += 1
        else:
            unstable.append(k)
    pct = round(100.0 * stable / max(1, len(keys)), 1)
    return {
        "pass": pct >= 80.0,
        "stable_pct": pct,
        "stable_n": stable,
        "n": len(keys),
        "unstable": unstable,
        "runs": len(run_fingerprints),
    }
