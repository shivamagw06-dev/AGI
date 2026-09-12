"""Data Quality Engine — score evidence 0–100; DO NOT PUBLISH below threshold."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import (
    EVIDENCE_QUALITY_PUBLISH_THRESHOLD,
    FRESHNESS_MAX_DAYS,
    QUALITY_DIMENSIONS,
)


def _clamp(n: float) -> float:
    return max(0.0, min(100.0, float(n)))


def evaluate_evidence_quality(
    *,
    documents: Optional[List[Dict[str, Any]]] = None,
    canonical_financials: Optional[Dict[str, Any]] = None,
    registry_items: Optional[List[Dict[str, Any]]] = None,
    governance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    docs = documents or []
    items = registry_items or []
    fin = canonical_financials or {}
    gov = governance or {}
    dims: Dict[str, float] = {}

    # Completeness
    periods = fin.get("periods") or []
    dims["completeness"] = _clamp(
        (40.0 if docs else 0.0)
        + (40.0 if periods else 0.0)
        + (20.0 if fin.get("published") else 0.0)
    )

    # Consistency / accounting
    accounting_ok = True
    for p in periods[:3]:
        inc = (p or {}).get("income_statement") or {}
        rev, ebitda = inc.get("revenue"), inc.get("ebitda")
        if rev and ebitda and abs(float(ebitda)) > abs(float(rev)) * 1.5:
            accounting_ok = False
    dims["consistency"] = 85.0 if periods and accounting_ok else (40.0 if periods else 10.0)
    dims["accounting_validation"] = 90.0 if periods and accounting_ok else (0.0 if periods else 20.0)

    # Freshness
    fresh = [i for i in items if i.get("freshness_ok")]
    if items:
        dims["freshness"] = _clamp(100.0 * len(fresh) / len(items))
    else:
        dims["freshness"] = 0.0
    stale = [
        i
        for i in items
        if (i.get("freshness_days") or 0) > FRESHNESS_MAX_DAYS
    ]
    if stale and not fresh:
        dims["freshness"] = min(dims["freshness"], 15.0)

    # Authority
    if items:
        auth = sum(float(i.get("authority_score") or 0) for i in items) / len(items)
        dims["authority"] = _clamp(auth * 100.0)
    elif gov.get("source_authority") is not None:
        dims["authority"] = _clamp(float(gov["source_authority"]) * 100.0)
    else:
        dims["authority"] = 20.0

    # Coverage
    dims["coverage"] = _clamp(min(100.0, len(docs) * 20.0 + len(periods) * 5.0))

    # Confidence
    confs = [float(i.get("confidence") or 0) for i in items if i.get("confidence") is not None]
    dims["confidence"] = _clamp((sum(confs) / len(confs) * 100.0) if confs else dims["authority"] * 0.7)

    # Duplicate detection — unique hashes
    hashes = [i.get("hash") for i in items if i.get("hash")]
    if hashes:
        uniq = len(set(hashes)) / len(hashes)
        dims["duplicate_detection"] = _clamp(uniq * 100.0)
    else:
        dims["duplicate_detection"] = 50.0 if not items else 20.0

    # Schema validation
    schema_ok = bool(fin.get("schema") or fin.get("periods") is not None or not fin)
    if fin and (fin.get("schema") or fin.get("period_count") is not None):
        schema_ok = True
    dims["schema_validation"] = 90.0 if schema_ok and (periods or not fin) else (60.0 if docs else 30.0)

    # Ensure all dimensions present
    for d in QUALITY_DIMENSIONS:
        dims.setdefault(d, 0.0)

    score = sum(dims.values()) / max(1, len(QUALITY_DIMENSIONS))
    score = round(_clamp(score), 2)
    publish_allowed = score >= EVIDENCE_QUALITY_PUBLISH_THRESHOLD
    return {
        "ok": True,
        "evidence_quality_score": score,
        "threshold": EVIDENCE_QUALITY_PUBLISH_THRESHOLD,
        "publish_allowed": publish_allowed,
        "status": "PUBLISHABLE" if publish_allowed else "DO NOT PUBLISH",
        "dimensions": {k: round(v, 2) for k, v in dims.items()},
        "rule": "If quality < threshold → DO NOT PUBLISH",
    }


def quality_publish_allowed(quality_result: Dict[str, Any]) -> bool:
    return bool(quality_result.get("publish_allowed"))
