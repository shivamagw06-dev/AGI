"""Business Analyst validation — mandate and evidence integrity."""

from __future__ import annotations

from typing import Any, Dict, List


def validate_mandate_scope(answer: str, forbidden_tokens: List[str]) -> List[str]:
    issues: List[str] = []
    lower = (answer or "").lower()
    for token in forbidden_tokens:
        if token.lower() in lower:
            issues.append(f"Out-of-mandate language detected: {token}")
    return issues


def validate_evidence_citations(claims: List[str], evidence: List[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []
    if claims and not evidence:
        issues.append("Claims present without cited evidence")
    cited = sum(1 for e in evidence if e.get("source_ref") or e.get("claim"))
    if claims and cited == 0:
        issues.append("Evidence items lack source references")
    return issues


def validate_opinion_completeness(opinion: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    required = [
        "business_quality",
        "moat_assessment",
        "competitive_outlook",
        "reasoning",
        "assumptions",
        "uncertainty",
        "unanswered_questions",
        "confidence",
    ]
    for key in required:
        if key not in opinion or opinion.get(key) in (None, "", [], {}):
            issues.append(f"Incomplete coverage: missing {key}")
    conf = opinion.get("confidence") or {}
    for key in ("evidence", "knowledge", "freshness", "overall"):
        if key not in conf:
            issues.append(f"Confidence incomplete: missing {key}")
    return issues


def run_validation(
    *,
    answer: str,
    claims: List[str],
    evidence: List[Dict[str, Any]],
    opinion: Dict[str, Any],
    forbidden_tokens: List[str],
) -> Dict[str, Any]:
    issues = []
    issues.extend(validate_mandate_scope(answer, forbidden_tokens))
    issues.extend(validate_evidence_citations(claims, evidence))
    issues.extend(validate_opinion_completeness(opinion))
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "issue_count": len(issues),
    }
