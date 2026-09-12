"""Missing Knowledge Inbox — prioritized gaps with ICC / readiness impact."""

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


def build_missing_inbox(*, scope: str = "TOP20", limit: int = 50) -> Dict[str, Any]:
    """Today's highest-impact missing knowledge with estimated ICC gain."""
    from institutional_coverage_factory.universe import top20_tickers, tier_for_ticker
    from institutional_coverage_factory.scorer.score import score_evidence_classes

    scope_u = str(scope or "TOP20").upper()
    if scope_u == "TOP20":
        tickers = top20_tickers()
    else:
        try:
            from institutional_coverage_factory.universe import ordered_universe

            tickers = [c["ticker"] for c in ordered_universe()]
            if scope_u == "NIFTY50":
                tickers = [t for t in tickers if tier_for_ticker(t) in {"TOP20", "NIFTY50"}]
            elif scope_u == "NIFTY100":
                tickers = [
                    t
                    for t in tickers
                    if tier_for_ticker(t) in {"TOP20", "NIFTY50", "NIFTY100"}
                ]
        except Exception:
            tickers = top20_tickers()

    items: List[Dict[str, Any]] = []
    for t in tickers:
        try:
            score = score_evidence_classes(t)
        except Exception:
            continue
        missing = list(score.get("missing_classes") or [])
        tier = tier_for_ticker(t)
        coverage = float(score.get("coverage_pct") or 0)
        for class_id in missing:
            priority = MISSING_PRIORITY.get(class_id, "Medium")
            label = CLASS_LABELS.get(class_id, class_id.replace("_", " ").title())
            weight = float(CLASS_WEIGHTS.get(class_id, 5))
            uploadable = class_id not in {"company_memory", "knowledge_graph"}
            items.append(
                {
                    "ticker": t,
                    "company": _company_name(t),
                    "missing": label,
                    "missing_class": class_id,
                    "priority": priority,
                    "priority_rank": PRIORITY_RANK.get(priority, 9),
                    "tier": tier,
                    "coverage_pct": coverage,
                    "estimated_icc_gain_pct": weight,
                    "estimated_research_improvement": round(weight * 0.7, 1),
                    "estimated_knowledge_confidence_improvement": round(weight * 0.5, 1),
                    "expected_claims": int(weight * 8),
                    "estimated_processing_minutes": 2 if uploadable else 1,
                    "uploadable": uploadable,
                    "impact_note": f"+{weight:.0f}% ICC if {label} acquired for {t}",
                }
            )

    items.sort(
        key=lambda r: (
            r.get("priority_rank", 9),
            0 if r.get("tier") == "TOP20" else 1,
            -(r.get("estimated_icc_gain_pct") or 0),
            -(float(r.get("coverage_pct") or 0)),
            r.get("ticker") or "",
        )
    )
    capped = items[: max(1, min(int(limit), 200))]
    by_priority: Dict[str, int] = {}
    for r in capped:
        p = r["priority"]
        by_priority[p] = by_priority.get(p, 0) + 1

    return {
        "ok": True,
        "title": "Today's Highest-Impact Missing Knowledge",
        "scope": scope_u,
        "count": len(capped),
        "total_gaps": len(items),
        "by_priority": by_priority,
        "items": capped,
        "workflow": "Clear the inbox — do not search for gaps.",
    }


def missing_for_ticker(ticker: str) -> Dict[str, Any]:
    from institutional_coverage_factory.scorer.score import score_evidence_classes

    t = str(ticker or "").upper().strip()
    score = score_evidence_classes(t)
    missing = list(score.get("missing_classes") or [])
    return {
        "ok": True,
        "ticker": t,
        "coverage_pct": score.get("coverage_pct"),
        "missing": [
            {
                "class_id": c,
                "label": CLASS_LABELS.get(c, c),
                "priority": MISSING_PRIORITY.get(c, "Medium"),
                "estimated_icc_gain_pct": CLASS_WEIGHTS.get(c, 5),
                "uploadable": c not in {"company_memory", "knowledge_graph"},
            }
            for c in missing
        ],
        "classes": score.get("classes"),
    }
