"""Claim operations — validation, selection, assembly."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_object.schema import CLAIM_TYPES, FORBIDDEN_CLAIM_TOKENS, ClaimType


def validate_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """Validate a single knowledge claim."""
    issues: list[str] = []
    stmt = str(claim.get("statement") or "").lower()
    state = str(claim.get("state") or "UNKNOWN")
    confidence = claim.get("confidence")

    for tok in FORBIDDEN_CLAIM_TOKENS:
        if tok in stmt:
            issues.append(f"forbidden_token:{tok}")

    if claim.get("claim_type") not in CLAIM_TYPES:
        issues.append("invalid_claim_type")

    if state == "SUPPORTED" and not claim.get("evidence_refs"):
        issues.append("supported_requires_evidence")

    if state == "CONTRADICTED" and not claim.get("contradictions"):
        issues.append("contradicted_requires_contradiction_refs")

    if confidence is not None:
        try:
            c = float(confidence)
            if c < 0 or c > 100:
                issues.append("confidence_out_of_range")
        except (TypeError, ValueError):
            issues.append("confidence_invalid")

    return {"valid": len(issues) == 0, "issues": issues, "claim_id": claim.get("claim_id")}


def select_relevant_claims(
    iko: dict[str, Any],
    *,
    claim_types: list[ClaimType] | None = None,
    states: list[str] | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Select claims relevant to an Ask or workflow."""
    claims = list(iko.get("claims") or [])
    if claim_types:
        allowed = set(claim_types)
        claims = [c for c in claims if c.get("claim_type") in allowed]
    if states:
        allowed_s = set(states)
        claims = [c for c in claims if c.get("state") in allowed_s]
    # Prefer supported/answered, then partial, surface contradictions
    rank = {"SUPPORTED": 0, "ANSWERED": 1, "PARTIAL": 2, "CONTRADICTED": 3, "UNDER_REVIEW": 4, "STALE": 5, "UNKNOWN": 6}
    claims.sort(key=lambda c: (rank.get(str(c.get("state")), 9), -float(c.get("confidence") or 0)))
    return claims[:limit]


def claims_for_investment_assessment(iko: dict[str, Any]) -> list[dict[str, Any]]:
    """Claims required for 'Should I buy?' style questions."""
    return select_relevant_claims(
        iko,
        claim_types=["business", "financial", "valuation", "risk", "investment"],
        limit=10,
    )


def assemble_claim_bullets(claims: list[dict[str, Any]]) -> list[str]:
    """Plain-language bullets from claims for response assembly."""
    out: list[str] = []
    for c in claims:
        st = c.get("state") or "UNKNOWN"
        conf = c.get("confidence")
        suffix = f" ({st}, {conf}% confidence)" if conf else f" ({st})"
        out.append(f"{c.get('statement', '').strip()}{suffix}")
    return out
