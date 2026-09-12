"""Claim extraction from normalized evidence — no LLM writers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from institutional_knowledge_object.schema import CLAIM_REGISTRY, claim_id


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _find_template(template_id: str) -> dict[str, Any] | None:
    for t in CLAIM_REGISTRY:
        if t["template_id"] == template_id:
            return t
    return None


def extract_claims_from_source(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract institutional claims from a normalized source."""
    entity_id = source.get("entity_id") or "ENTITY"
    claims: list[dict[str, Any]] = []

    for extract in source.get("extracts") or []:
        if not isinstance(extract, dict):
            continue
        template_id = extract.get("template_id")
        statement = extract.get("statement")
        if not statement:
            continue

        evidence_id = extract.get("evidence_id") or f"EV_{source['source_id']}_{len(claims)}"
        confidence = int(extract.get("confidence") or min(source.get("trust_score", 70), 85))
        state = extract.get("state") or ("SUPPORTED" if confidence >= 70 else "PARTIAL")

        claim = {
            "claim_id": extract.get("claim_id") or (
                claim_id(entity_id, template_id) if template_id else f"CLAIM_{entity_id}_EXTRACT_{len(claims):03d}"
            ),
            "entity_id": entity_id,
            "entity_type": "company",
            "template_id": template_id,
            "statement": statement,
            "claim_type": extract.get("claim_type") or (_find_template(template_id) or {}).get("claim_type", "business"),
            "category": extract.get("category") or (_find_template(template_id) or {}).get("category", "business_model"),
            "state": state,
            "confidence": confidence,
            "evidence_refs": [{"evidence_id": evidence_id, "source_id": source["source_id"]}],
            "contradictions": list(extract.get("contradictions") or []),
            "dependencies": list(extract.get("dependencies") or []),
            "monitoring": extract.get("monitoring"),
            "reasoning_summary": extract.get("reasoning_summary"),
            "owner": "evidence_pipeline",
            "last_review": _now_iso(),
            "version": 1,
            "source_trust": source.get("trust_score"),
            "source_freshness": source.get("freshness"),
            "fabricated": False,
            "llm_used": False,
        }
        claims.append(claim)

    # Metric-triggered claim hints (deterministic, no LLM)
    metrics = source.get("metrics") or {}
    if metrics.get("operating_margin") is not None:
        margin = float(metrics["operating_margin"])
        tmpl = _find_template("CLAIM_MONITORING_MARGIN")
        if tmpl:
            claims.append({
                "claim_id": claim_id(entity_id, "CLAIM_MONITORING_MARGIN"),
                "entity_id": entity_id,
                "entity_type": "company",
                "template_id": "CLAIM_MONITORING_MARGIN",
                "statement": f"{entity_id} operating margins at {margin:.1f}%.",
                "claim_type": "monitoring",
                "category": "monitoring",
                "state": "SUPPORTED" if margin >= 20 else "UNDER_REVIEW",
                "confidence": 75 if margin >= 20 else 55,
                "evidence_refs": [{"evidence_id": f"EV_{source['source_id']}_MARGIN", "source_id": source["source_id"]}],
                "contradictions": [],
                "dependencies": [],
                "monitoring": {
                    "trigger": "operating_margin < 20%",
                    "status": "healthy" if margin >= 20 else "breached",
                    "metrics": ["operating_margin"],
                    "last_checked": _now_iso(),
                },
                "owner": "evidence_pipeline",
                "last_review": _now_iso(),
                "version": 1,
                "fabricated": False,
                "llm_used": False,
            })

    return claims


def extract_claims(normalized_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract all claims from normalized sources."""
    all_claims: list[dict[str, Any]] = []
    for source in normalized_sources:
        all_claims.extend(extract_claims_from_source(source))
    return all_claims
