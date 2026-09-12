"""ICE-01 production façades — committee review / Mission Control Committee Center."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Optional

from institutional_committee.committee_engine import generate_committee_resolution
from institutional_committee.diagnostics import build_diagnostics
from institutional_committee.flags import flags_dict, is_enabled
from institutional_committee import history as committee_history
from institutional_committee.schema import (
    DEFAULT_COMMITTEE_ID,
    DEFAULT_PORTFOLIO_ID,
    COMMITTEE_ENGINE_VERSION,
    ICE_PRODUCT,
    ICE_ROLE,
    ICE_SPEC,
    ICE_VERSION,
    ICE_WORKSTREAM_ID,
    VALIDATOR_VERSION,
)
from institutional_committee.validator import validate_resolution

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    committee_history.reset_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": ICE_WORKSTREAM_ID,
        "product": ICE_PRODUCT,
        "version": ICE_VERSION,
        "role": ICE_ROLE,
        "llm": False,
        "predictive": False,
        "mutates_upstream": False,
        "governs_cio_decisions": True,
        "executes_trades": False,
        "committee_engine_version": COMMITTEE_ENGINE_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": ICE_SPEC,
        "brand": "AGI",
        "phase": 4,
        "history": committee_history.metrics(),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    rows = committee_history.all_resolutions()
    pending = [r for r in rows if r.status == "Pending Review"]
    deferred = [r for r in rows if r.status == "Deferred"]
    escalations = [
        r
        for r in rows
        if r.status == "Escalated" or r.policy_status in {"Breach", "Critical Breach"}
    ]
    open_actions = []
    for r in rows:
        for a in r.required_actions:
            open_actions.append(a)
    overdue = [
        r
        for r in rows
        if r.status in {"Pending Review", "Deferred", "Escalated"}
        and r.review_date
        and "Immediate" in (r.review_date or "")
    ]
    upcoming = list(
        dict.fromkeys(
            [r.review_date for r in rows if r.review_date]
            + [f for r in rows for f in r.follow_up_items]
        )
    )[:12]
    return {
        "status": h.get("status"),
        "workstream_id": ICE_WORKSTREAM_ID,
        "product": ICE_PRODUCT,
        "version": ICE_VERSION,
        "llm": False,
        "committee_center": True,
        "pending_reviews": len(pending),
        "policy_escalations": len(escalations),
        "deferred_decisions": len(deferred),
        "upcoming_meetings": upcoming[:6],
        "open_action_items": len(open_actions),
        "overdue_reviews": len(overdue),
        "latest_resolution": rows[-1].to_dict() if rows else None,
        "resolutions_cached": len(rows),
    }


def _load_decision_stack(portfolio_id: str, policy_profile: str = "family_office") -> dict[str, Any]:
    """Load CIO decision + PRE risk + PCE policy for committee review."""
    out: dict[str, Any] = {
        "decision": None,
        "decision_obj": None,
        "risk": None,
        "risk_obj": None,
        "policy": None,
        "policy_obj": None,
        "errors": [],
    }

    try:
        from institutional_portfolio_decision.production import decide_portfolio
        from institutional_portfolio_decision import history as decision_history

        result = decide_portfolio({"portfolio_id": portfolio_id, "policy": policy_profile})
        if not result.get("ok"):
            out["errors"].append("CIO-01 decision unavailable")
            out["errors"].extend(list(result.get("validation_errors") or []))
            return out
        out["decision"] = result.get("decision")
        out["decision_obj"] = decision_history.latest(portfolio_id)
    except Exception as exc:  # noqa: BLE001
        out["errors"].append(f"CIO-01 unavailable: {exc}")
        return out

    try:
        from institutional_portfolio_risk.production import get_risk_object

        out["risk_obj"] = get_risk_object(portfolio_id)
        if out["risk_obj"] is not None:
            out["risk"] = out["risk_obj"].to_dict()
    except Exception:  # noqa: BLE001
        pass

    try:
        from institutional_policy.production import get_assessment_object

        out["policy_obj"] = get_assessment_object(portfolio_id, policy_profile)
        if out["policy_obj"] is not None:
            out["policy"] = out["policy_obj"].to_dict()
    except Exception:  # noqa: BLE001
        pass

    # Soft-fill ids from decision if objects missing
    decision = out["decision"] or {}
    if not out.get("risk") and decision.get("portfolio_risk_id"):
        out["risk"] = {
            "risk_id": decision.get("portfolio_risk_id"),
            "overall_risk": decision.get("overall_risk"),
        }
    if not out.get("policy") and decision.get("policy_id"):
        out["policy"] = {
            "policy_id": decision.get("policy_id"),
            "overall_status": decision.get("policy_status"),
            "violations": (decision.get("policy_summary") or {}).get("primary_violation")
            and [(decision.get("policy_summary") or {}).get("primary_violation")]
            or [],
            "violation_count": (decision.get("policy_summary") or {}).get("violation_count") or 0,
            "required_actions": (decision.get("policy_summary") or {}).get("required_actions") or [],
        }

    return out


def review_committee(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": ICE_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["ICE-01 disabled"],
        }

    t0 = time.perf_counter()
    body = dict(payload or {})
    portfolio_id = str(body.get("portfolio_id") or body.get("portfolio") or DEFAULT_PORTFOLIO_ID).strip()
    if portfolio_id in {"default", "DEFAULT"}:
        portfolio_id = DEFAULT_PORTFOLIO_ID
    policy_profile = str(body.get("policy") or body.get("profile_id") or "family_office")
    committee_id = str(body.get("committee_id") or DEFAULT_COMMITTEE_ID)

    stack = _load_decision_stack(portfolio_id, policy_profile)
    if stack["errors"] or not stack.get("decision"):
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": ICE_WORKSTREAM_ID,
            "validation_errors": stack["errors"] or ["portfolio decision unavailable"],
        }

    prev = committee_history.latest(portfolio_id)
    resolution = generate_committee_resolution(
        portfolio_decision=stack.get("decision_obj") or stack["decision"],
        portfolio_risk=stack.get("risk_obj") or stack.get("risk"),
        policy_assessment=stack.get("policy_obj") or stack.get("policy"),
        previous_version=prev.resolution_version if prev else 0,
        committee_id=committee_id,
    )

    prelim = build_diagnostics(resolution, latency_ms=(time.perf_counter() - t0) * 1000.0)
    resolution = replace(resolution, diagnostics=prelim)

    validation = validate_resolution(resolution)
    diag = build_diagnostics(
        resolution,
        validation=validation.to_dict(),
        latency_ms=(time.perf_counter() - t0) * 1000.0,
    )
    resolution = replace(resolution, diagnostics=diag)

    if not validation.ok:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": ICE_WORKSTREAM_ID,
            "validation_errors": list(validation.errors),
            "gates": validation.gates,
            "resolution": resolution.to_dict(),
            "diagnostics": diag,
            "llm": False,
            "mutates_upstream": False,
        }

    committee_history.record(resolution)
    return {
        "ok": True,
        "rejected": False,
        "workstream_id": ICE_WORKSTREAM_ID,
        "product": ICE_PRODUCT,
        "version": ICE_VERSION,
        "resolution": resolution.to_dict(),
        "diagnostics": diag,
        "portfolio_decision_id": resolution.portfolio_decision_id,
        "mutates_upstream": False,
        "llm": False,
    }


def get_resolution(resolution_id: str) -> dict[str, Any]:
    r = committee_history.get(resolution_id)
    if r is None:
        return {
            "ok": False,
            "workstream_id": ICE_WORKSTREAM_ID,
            "error": "resolution_not_found",
            "resolution_id": resolution_id,
        }
    return {
        "ok": True,
        "workstream_id": ICE_WORKSTREAM_ID,
        "resolution": r.to_dict(),
        "diagnostics": r.diagnostics,
        "mutates_upstream": False,
        "llm": False,
    }


def get_pending() -> dict[str, Any]:
    rows = committee_history.pending()
    return {
        "ok": True,
        "workstream_id": ICE_WORKSTREAM_ID,
        "pending": [r.to_dict() for r in rows],
        "count": len(rows),
        "llm": False,
    }


def get_portfolio_resolutions(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    *,
    refresh: bool = True,
) -> dict[str, Any]:
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip()
    if pid in {"default", "DEFAULT"}:
        pid = DEFAULT_PORTFOLIO_ID
    if refresh or committee_history.latest(pid) is None:
        result = review_committee({"portfolio_id": pid})
        if result.get("ok"):
            result = dict(result)
            result["history"] = committee_history.list_for_portfolio(pid)
        return result
    latest = committee_history.latest(pid)
    assert latest is not None
    return {
        "ok": True,
        "workstream_id": ICE_WORKSTREAM_ID,
        "resolution": latest.to_dict(),
        "diagnostics": latest.diagnostics,
        "history": committee_history.list_for_portfolio(pid),
        "cached": True,
        "mutates_upstream": False,
        "llm": False,
    }
