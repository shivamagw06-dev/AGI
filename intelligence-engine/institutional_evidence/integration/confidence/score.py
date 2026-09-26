"""Knowledge Confidence — separate from Research Confidence."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..schema import KNOWLEDGE_CONFIDENCE_THRESHOLD, KNOWLEDGE_CONFIDENCE_WEIGHTS


def _clamp(n: float) -> float:
    return max(0.0, min(100.0, float(n)))


def compute_knowledge_confidence(
    ticker: str,
    *,
    transformed: Optional[Dict[str, Any]] = None,
    pack: Optional[Dict[str, Any]] = None,
    timeline: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    t = str(ticker or "").upper()
    models = (transformed or {}).get("models") or {}
    fin = models.get("CanonicalFinancialStatements") or (pack or {}).get("financials") or {}
    periods = fin.get("periods") or []
    annuals = [p for p in periods if (p or {}).get("period_type") == "annual"]
    reg_items = ((pack or {}).get("evidence") or {}).get("registry") or {}
    if isinstance(reg_items, dict):
        items = reg_items.get("items") or []
    else:
        items = []
    tl = timeline or {}
    event_count = int(tl.get("event_count") or 0)

    components = {
        "financial_coverage": _clamp(
            100.0 if len(annuals) >= 10 else (len(annuals) / 10.0) * 100.0 if annuals else (40.0 if periods else 0.0)
        ),
        "evidence_coverage": _clamp(min(100.0, len(items) * 25.0)),
        "timeline_completeness": _clamp(min(100.0, event_count * 20.0)),
        "management_coverage": 60.0
        if (models.get("CanonicalManagementGuidance") or {}).get("guidance_items")
        else (30.0 if periods else 0.0),
        "segment_coverage": 80.0 if fin.get("segment_revenue") else (20.0 if periods else 0.0),
        "transcript_coverage": 70.0
        if (models.get("CanonicalTranscript") or {}).get("highlights")
        else 0.0,
        "valuation_coverage": 80.0
        if (models.get("CanonicalValuation") or {}).get("multiples")
        or (models.get("CanonicalValuation") or {}).get("evidence_refs")
        else (30.0 if periods else 0.0),
        "historical_depth": _clamp(
            min(100.0, (len(annuals) / 20.0) * 100.0) if annuals else (50.0 if periods else 0.0)
        ),
        "freshness": _clamp(
            100.0
            * (
                sum(1 for i in items if i.get("freshness_ok")) / len(items)
                if items
                else (0.5 if periods else 0.0)
            )
        ),
    }

    weighted = 0.0
    detail = {}
    for key, weight in KNOWLEDGE_CONFIDENCE_WEIGHTS.items():
        score = float(components.get(key, 0.0))
        weighted += (score / 100.0) * weight
        detail[key] = {"score": round(score, 2), "weight": weight}

    overall = round(_clamp(weighted), 2)
    return {
        "ok": True,
        "ticker": t,
        "knowledge_confidence": overall,
        "threshold": KNOWLEDGE_CONFIDENCE_THRESHOLD,
        "above_threshold": overall >= KNOWLEDGE_CONFIDENCE_THRESHOLD,
        "components": detail,
        "rule": "Research Confidence and Knowledge Confidence remain separate metrics",
    }
