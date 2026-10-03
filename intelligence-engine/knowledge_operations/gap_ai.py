"""Knowledge Gap AI — continuous analysis of missing institutional evidence impact."""

from __future__ import annotations

from typing import Any, Dict, List

from knowledge_operations.schema import (
    CLASS_LABELS,
    CLASS_WEIGHTS,
    MISSING_PRIORITY,
    PRIORITY_RANK,
)


def _company_name(ticker: str) -> str:
    try:
        from institutional_evidence.schema import PHASE1_TOP20

        for row in PHASE1_TOP20:
            if row["ticker"] == ticker:
                return str(row["company"])
    except Exception:
        pass
    return ticker


def analyze_gaps(*, scope: str = "TOP20", limit: int = 30) -> Dict[str, Any]:
    """
    For each company with gaps, estimate coverage / confidence / readiness uplift
    if missing evidence were acquired.
    """
    from institutional_coverage_factory.universe import top20_tickers, tier_for_ticker
    from institutional_coverage_factory.scorer.score import score_evidence_classes
    from institutional_coverage_factory.validator.icc import evaluate_icc

    tickers = top20_tickers() if str(scope or "TOP20").upper() == "TOP20" else top20_tickers()
    analyses: List[Dict[str, Any]] = []

    for t in tickers:
        try:
            score = score_evidence_classes(t)
            icc = evaluate_icc(t, score=score)
        except Exception:
            continue
        missing = list(score.get("missing_classes") or [])
        if not missing:
            continue
        current = float(score.get("coverage_pct") or 0)
        gain = sum(float(CLASS_WEIGHTS.get(c, 5)) for c in missing)
        expected = min(100.0, round(current + gain, 1))
        # Soft confidence / readiness uplift proxies
        kc_now = float(icc.get("knowledge_confidence") or 0)
        rr_now = float(icc.get("research_readiness_score") or 0)
        kc_gain = min(100.0 - kc_now, round(gain * 0.5, 1))
        rr_gain = min(100.0 - rr_now, round(gain * 0.7, 1))
        expected_claims = int(round(gain * 8))
        eta_min = max(1, int(round(len(missing) * 0.75)))
        analyses.append(
            {
                "ticker": t,
                "company": _company_name(t),
                "tier": tier_for_ticker(t),
                "missing": [CLASS_LABELS.get(c, c) for c in missing],
                "missing_classes": missing,
                "priority": MISSING_PRIORITY.get(missing[0], "Medium") if missing else "Low",
                "priority_rank": min(PRIORITY_RANK.get(MISSING_PRIORITY.get(c, "Medium"), 9) for c in missing),
                "coverage_now": current,
                "coverage_expected": expected,
                "coverage_gain_pct": round(expected - current, 1),
                "knowledge_confidence_now": kc_now,
                "knowledge_confidence_expected": round(min(100.0, kc_now + kc_gain), 1),
                "research_ready_now": rr_now,
                "research_ready_expected": round(min(100.0, rr_now + rr_gain), 1),
                "estimated_new_claims": expected_claims,
                "estimated_processing_minutes": eta_min,
                "claim_safe": bool(icc.get("claim_safe")),
            }
        )

    analyses.sort(
        key=lambda r: (
            r.get("priority_rank", 9),
            -(r.get("coverage_gain_pct") or 0),
            r.get("ticker") or "",
        )
    )
    capped = analyses[: max(1, min(int(limit), 100))]
    return {
        "ok": True,
        "title": "Knowledge Gap AI",
        "scope": scope,
        "count": len(capped),
        "items": capped,
        "action": "Find Missing Knowledge",
        "note": "Estimates are weight-based from the Institutional Coverage model; clearing gaps raises ICC toward 100%.",
    }


def find_missing_knowledge(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    full = analyze_gaps(scope="TOP20", limit=100)
    hit = next((i for i in full.get("items") or [] if i.get("ticker") == t), None)
    if hit:
        return {"ok": True, "ticker": t, "analysis": hit}
    return {
        "ok": True,
        "ticker": t,
        "analysis": {
            "ticker": t,
            "missing": [],
            "coverage_now": None,
            "coverage_expected": None,
            "note": "No gaps detected in current score, or company outside scanned scope.",
        },
    }
