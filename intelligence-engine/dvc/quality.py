"""Data quality scores and institutional grade gates."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dvc.schema import (
    DVC_VERSION,
    FUNDAMENTAL_FIELDS,
    GRADE_THRESHOLDS,
    QUOTE_FIELDS,
)


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def coverage_score(validated_fields: Dict[str, Any], expected: List[str]) -> float:
    if not expected:
        return 1.0
    present = 0
    for f in expected:
        vf = validated_fields.get(f) or {}
        if isinstance(vf, dict) and vf.get("value") not in (None, ""):
            present += 1
    return round(present / len(expected), 4)


def freshness_score(validated_fields: Dict[str, Any], *, max_age_hours: float = 24.0) -> float:
    ages: List[float] = []
    now = datetime.now(timezone.utc)
    for vf in validated_fields.values():
        if not isinstance(vf, dict):
            continue
        ts = _parse_ts(vf.get("verified_at") or vf.get("timestamp"))
        if not ts:
            continue
        age_h = max(0.0, (now - ts).total_seconds() / 3600.0)
        ages.append(age_h)
    if not ages:
        return 0.5
    avg_age = sum(ages) / len(ages)
    # 1.0 if fresh, decays to 0 at max_age_hours*2
    score = max(0.0, 1.0 - (avg_age / (max_age_hours * 2)))
    return round(score, 4)


def confidence_score(validated_fields: Dict[str, Any]) -> float:
    confs = [
        float(vf.get("confidence") or 0)
        for vf in validated_fields.values()
        if isinstance(vf, dict) and vf.get("value") not in (None, "")
    ]
    if not confs:
        return 0.0
    return round(sum(confs) / len(confs), 4)


def consistency_score(conflicts: List[Dict[str, Any]]) -> float:
    if not conflicts:
        return 1.0
    penalty = 0.0
    for c in conflicts:
        sev = str(c.get("severity") or "low")
        penalty += {"low": 0.02, "medium": 0.08, "high": 0.18, "critical": 0.35}.get(sev, 0.05)
    return round(max(0.0, 1.0 - penalty), 4)


def provider_agreement_score(
    validated_fields: Dict[str, Any],
    observations_by_field: Dict[str, List[Dict[str, Any]]],
) -> float:
    agreements: List[float] = []
    for field, vf in validated_fields.items():
        if not isinstance(vf, dict) or vf.get("value") in (None, ""):
            continue
        obs = observations_by_field.get(field) or []
        if len(obs) < 2:
            agreements.append(1.0)
            continue
        # fraction of providers within consensus (not rejected)
        rejected = {str(r.get("provider")) for r in (vf.get("rejected_providers") or []) if isinstance(r, dict)}
        total = len(obs)
        agreed = total - len(rejected)
        agreements.append(max(0.0, agreed / total))
    if not agreements:
        return 0.5
    return round(sum(agreements) / len(agreements), 4)


def validation_score(validated_fields: Dict[str, Any]) -> float:
    statuses = [
        str(vf.get("validation_status") or "")
        for vf in validated_fields.values()
        if isinstance(vf, dict) and vf.get("value") not in (None, "")
    ]
    if not statuses:
        return 0.0
    ok = sum(1 for s in statuses if s in ("validated", "consensus", "single_source"))
    return round(ok / len(statuses), 4)


def compute_quality(
    validated_fields: Dict[str, Any],
    *,
    conflicts: Optional[List[Dict[str, Any]]] = None,
    observations_by_field: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    kind: str = "combined",
) -> Dict[str, Any]:
    conflicts = conflicts or []
    observations_by_field = observations_by_field or {}
    if kind == "quote":
        expected = list(QUOTE_FIELDS)
    elif kind == "fundamentals":
        expected = list(FUNDAMENTAL_FIELDS)
    else:
        expected = list(dict.fromkeys([*QUOTE_FIELDS, *FUNDAMENTAL_FIELDS]))

    coverage = coverage_score(validated_fields, expected)
    freshness = freshness_score(validated_fields)
    confidence = confidence_score(validated_fields)
    consistency = consistency_score(conflicts)
    agreement = provider_agreement_score(validated_fields, observations_by_field)
    validation = validation_score(validated_fields)
    overall = round(
        coverage * 0.25
        + freshness * 0.2
        + confidence * 0.25
        + consistency * 0.15
        + agreement * 0.05
        + validation * 0.1,
        4,
    )
    return {
        "coverage": coverage,
        "freshness": freshness,
        "confidence": confidence,
        "consistency": consistency,
        "provider_agreement": agreement,
        "validation": validation,
        "overall": overall,
        "expected_fields": expected,
        "dvc_version": DVC_VERSION,
    }


def grade_from_quality(quality: Dict[str, Any]) -> Dict[str, Any]:
    """Map quality scores → Research / Knowledge / Data grades + institutional gate."""
    overall = float(quality.get("overall") or 0)
    coverage = float(quality.get("coverage") or 0)
    freshness = float(quality.get("freshness") or 0)
    confidence = float(quality.get("confidence") or 0)
    consistency = float(quality.get("consistency") or 0)
    validation = float(quality.get("validation") or 0)

    def _band(score: float) -> str:
        if score >= 0.95:
            return "A"
        if score >= 0.85:
            return "B"
        if score >= 0.7:
            return "C"
        if score >= 0.5:
            return "D"
        return "F"

    data_grade = _band(overall)
    research_grade = _band(min(coverage, confidence, consistency))
    knowledge_grade = _band(min(freshness, validation, overall))

    t = GRADE_THRESHOLDS
    institutional = (
        coverage >= float(t.get("coverage", 0.9))
        and freshness >= float(t.get("freshness", 0.85))
        and confidence >= float(t.get("confidence", 0.9))
        and consistency >= float(t.get("consistency", 0.9))
        and validation >= float(t.get("validation", 0.9))
    )
    return {
        "research_grade": "Institutional" if institutional else research_grade,
        "knowledge_grade": knowledge_grade,
        "data_grade": data_grade,
        "institutional": institutional,
        "gates": {
            "coverage": coverage >= float(t.get("coverage", 0.9)),
            "freshness": freshness >= float(t.get("freshness", 0.85)),
            "confidence": confidence >= float(t.get("confidence", 0.9)),
            "consistency": consistency >= float(t.get("consistency", 0.9)),
            "validation": validation >= float(t.get("validation", 0.9)),
        },
    }


def missing_fields(validated_fields: Dict[str, Any], expected: Optional[List[str]] = None) -> List[str]:
    expected = expected or list(dict.fromkeys([*QUOTE_FIELDS, *FUNDAMENTAL_FIELDS]))
    out = []
    for f in expected:
        vf = validated_fields.get(f) or {}
        if not isinstance(vf, dict) or vf.get("value") in (None, ""):
            out.append(f)
    return out
