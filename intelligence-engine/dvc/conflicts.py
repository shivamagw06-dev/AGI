"""Conflict detection across multi-provider observations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dvc.priority import provider_priority
from dvc.schema import CONFLICT_FIELDS, CONFLICT_THRESHOLDS, DVC_VERSION


def _num(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _severity_for_spread(field: str, values: List[float]) -> str:
    if len(values) < 2:
        return "low"
    lo, hi = min(values), max(values)
    if lo == 0:
        spread = abs(hi - lo)
    else:
        spread = abs(hi - lo) / abs(lo)
    thresholds = CONFLICT_THRESHOLDS.get(field, {"medium": 0.05, "high": 0.15, "critical": 0.5})
    if spread >= float(thresholds.get("critical", 0.5)):
        return "critical"
    if spread >= float(thresholds.get("high", 0.15)):
        return "high"
    if spread >= float(thresholds.get("medium", 0.05)):
        return "medium"
    return "low"


def detect_conflicts(
    observations_by_field: Dict[str, List[Dict[str, Any]]],
    *,
    company_id: str = "",
) -> List[Dict[str, Any]]:
    """Generate conflict reports for fields with material provider disagreement."""
    reports: List[Dict[str, Any]] = []
    for field in CONFLICT_FIELDS:
        obs = list(observations_by_field.get(field) or [])
        if len(obs) < 2:
            continue
        nums = [(o.get("provider"), _num(o.get("value"))) for o in obs]
        nums = [(p, v) for p, v in nums if v is not None]
        cats = [(o.get("provider"), o.get("value")) for o in obs if _num(o.get("value")) is None and o.get("value") not in (None, "")]
        if len(nums) >= 2:
            vals = [v for _, v in nums]
            severity = _severity_for_spread(field, vals)
            if severity == "low":
                continue
            ranked = sorted(nums, key=lambda x: provider_priority(str(x[0])))
            winner_p, winner_v = ranked[0]
            rejected = [
                {"provider": p, "value": v, "reason": "lower_priority_or_outlier"}
                for p, v in ranked[1:]
            ]
            reports.append(
                {
                    "company_id": company_id,
                    "field": field,
                    "severity": severity,
                    "values": [{"provider": p, "value": v} for p, v in ranked],
                    "canonical_value": winner_v,
                    "winning_provider": winner_p,
                    "rejected_providers": rejected,
                    "reason": f"Numeric discrepancy on {field} (severity={severity})",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "dvc_version": DVC_VERSION,
                    "status": "open",
                }
            )
        elif len(cats) >= 2:
            uniq = {str(v).strip().lower() for _, v in cats}
            if len(uniq) <= 1:
                continue
            ranked = sorted(cats, key=lambda x: provider_priority(str(x[0])))
            winner_p, winner_v = ranked[0]
            reports.append(
                {
                    "company_id": company_id,
                    "field": field,
                    "severity": "medium",
                    "values": [{"provider": p, "value": v} for p, v in ranked],
                    "canonical_value": winner_v,
                    "winning_provider": winner_p,
                    "rejected_providers": [
                        {"provider": p, "value": v, "reason": "categorical_mismatch"}
                        for p, v in ranked[1:]
                    ],
                    "reason": f"Categorical conflict on {field}",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                    "dvc_version": DVC_VERSION,
                    "status": "open",
                }
            )
    return reports


def conflict_summary(reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_sev = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for r in reports:
        s = str(r.get("severity") or "low")
        by_sev[s] = by_sev.get(s, 0) + 1
    open_n = sum(1 for r in reports if str(r.get("status") or "open") == "open")
    return {
        "total": len(reports),
        "open": open_n,
        "by_severity": by_sev,
        "highest": (
            "critical"
            if by_sev.get("critical")
            else "high"
            if by_sev.get("high")
            else "medium"
            if by_sev.get("medium")
            else "low"
            if reports
            else "none"
        ),
    }
