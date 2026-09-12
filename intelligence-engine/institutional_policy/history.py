"""In-memory versioned history for InstitutionalPolicyAssessment."""

from __future__ import annotations

from typing import Any, Optional

from institutional_policy.models import InstitutionalPolicyAssessment

_HISTORY: dict[str, list[InstitutionalPolicyAssessment]] = {}


def reset_for_tests() -> None:
    _HISTORY.clear()


def _key(portfolio_id: str, profile_id: str = "") -> str:
    if profile_id:
        return f"{portfolio_id}|{profile_id}"
    return str(portfolio_id)


def record(assessment: InstitutionalPolicyAssessment) -> None:
    key = _key(assessment.portfolio_id, assessment.profile_id)
    _HISTORY.setdefault(key, []).append(assessment)
    # Also index by portfolio alone for latest-any-profile lookup
    _HISTORY.setdefault(assessment.portfolio_id, []).append(assessment)
    for k in (key, assessment.portfolio_id):
        if len(_HISTORY[k]) > 100:
            _HISTORY[k] = _HISTORY[k][-100:]


def latest(portfolio_id: str, profile_id: str = "") -> Optional[InstitutionalPolicyAssessment]:
    key = _key(str(portfolio_id) or "", profile_id) if profile_id else str(portfolio_id or "")
    rows = _HISTORY.get(key, [])
    return rows[-1] if rows else None


def list_versions(portfolio_id: str, profile_id: str = "") -> list[dict[str, Any]]:
    key = _key(str(portfolio_id) or "", profile_id) if profile_id else str(portfolio_id or "")
    rows = _HISTORY.get(key, [])
    return [
        {
            "policy_id": a.policy_id,
            "policy_version": a.policy_version,
            "profile_id": a.profile_id,
            "overall_status": a.overall_status,
            "compliance_score": a.compliance_score,
            "generated_at": a.generated_at,
        }
        for a in rows
    ]


def metrics() -> dict[str, Any]:
    portfolios = sorted({k.split("|")[0] for k in _HISTORY if "|" not in k or True})
    # Count unique assessments via portfolio-only keys
    assessed = [k for k in _HISTORY if "|" not in k]
    return {
        "portfolios": sorted(assessed),
        "assessment_count": sum(len(_HISTORY[k]) for k in assessed),
        "breach_count": sum(
            1
            for k in assessed
            for a in _HISTORY[k]
            if a.overall_status in {"Breach", "Critical Breach"}
        ),
    }
