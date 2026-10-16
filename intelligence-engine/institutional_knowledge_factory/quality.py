"""Knowledge quality metrics — measured, not assumed."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_factory.schema import QUALITY_METRICS


def compute_knowledge_quality(iko: dict[str, Any]) -> dict[str, Any]:
    """Compute knowledge quality metrics for a company IKO."""
    claims = list(iko.get("claims") or [])
    total = len(claims) or 1
    required = [c for c in claims if c.get("required") is not False]
    required_total = len(required) or total

    non_unknown = [c for c in claims if str(c.get("state")) != "UNKNOWN"]
    with_evidence = [c for c in claims if c.get("evidence_refs")]
    contradicted = [c for c in claims if str(c.get("state")) == "CONTRADICTED"]
    unknown = [c for c in claims if str(c.get("state")) == "UNKNOWN"]
    required_addressed = [c for c in required if str(c.get("state")) != "UNKNOWN"]

    freshness_scores = [
        float(c.get("source_freshness") or 70)
        for c in claims if c.get("evidence_refs")
    ]
    trust_scores = [
        float(c.get("source_trust") or 70)
        for c in claims if c.get("evidence_refs")
    ]

    avg_freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 0
    avg_trust = sum(trust_scores) / len(trust_scores) if trust_scores else 0
    data_quality = (avg_freshness * 0.4 + avg_trust * 0.6) if freshness_scores else 0

    stale_count = sum(1 for c in claims if str(c.get("state")) == "STALE")
    under_review = sum(1 for c in claims if str(c.get("state")) == "UNDER_REVIEW")

    if contradicted or under_review > 2:
        review_status = "needs_review"
    elif stale_count > 0 or avg_freshness < 50:
        review_status = "stale"
    else:
        review_status = "healthy"

    metrics = {
        "knowledge_coverage": round(100.0 * len(non_unknown) / total, 1),
        "assertion_coverage": round(100.0 * len(required_addressed) / required_total, 1),
        "evidence_coverage": round(100.0 * len(with_evidence) / total, 1),
        "freshness": round(avg_freshness, 1),
        "contradiction_count": len(contradicted),
        "unknown_count": len(unknown),
        "data_quality": round(data_quality, 1),
        "review_status": review_status,
        "total_claims": total,
        "supported_count": sum(1 for c in claims if str(c.get("state")) == "SUPPORTED"),
    }

    return {
        "entity_id": iko.get("entity_id"),
        "metrics": metrics,
        "quality_dimensions": list(QUALITY_METRICS),
        "no_percentages_assumed": False,
        "measured": True,
    }
