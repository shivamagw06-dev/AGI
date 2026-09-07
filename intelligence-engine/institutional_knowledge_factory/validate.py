"""Evidence and assertion validation."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_object.claims import validate_claim


def validate_extracted_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """Validate an extracted claim against institutional rules."""
    base = validate_claim(claim)
    issues = list(base.get("issues") or [])

    # Assertion validation questions from spec
    checks = {
        "has_supporting_evidence": bool(claim.get("evidence_refs")),
        "evidence_recent": (claim.get("source_freshness") or 0) >= 50,
        "evidence_reliable": (claim.get("source_trust") or 0) >= 60,
        "reproducible": claim.get("llm_used") is not True,
        "has_statement": bool(str(claim.get("statement") or "").strip()),
    }

    state = str(claim.get("state") or "UNKNOWN")
    if state in {"SUPPORTED", "PARTIAL", "ANSWERED"} and not checks["has_supporting_evidence"]:
        issues.append("assertion_requires_evidence")
        claim = dict(claim)
        claim["state"] = "UNKNOWN"
        claim["confidence"] = 0

    return {
        **base,
        "valid": len(issues) == 0,
        "issues": issues,
        "checks": checks,
        "claim": claim,
    }


def validate_evidence_batch(claims: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate batch; return (valid_claims, validation_reports)."""
    valid: list[dict[str, Any]] = []
    reports: list[dict[str, Any]] = []
    for claim in claims:
        result = validate_extracted_claim(claim)
        reports.append(result)
        if result.get("valid") or result.get("claim"):
            valid.append(result.get("claim") or claim)
    return valid, reports
