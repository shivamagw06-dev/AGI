"""PCE-01 production façades — policy check / Mission Control Policy Center."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Optional

from institutional_policy.diagnostics import build_diagnostics
from institutional_policy.flags import flags_dict, is_enabled
from institutional_policy import history as policy_history
from institutional_policy.mandates import list_profiles
from institutional_policy.policy_engine import generate_policy_assessment
from institutional_policy.schema import (
    DEFAULT_POLICY_PROFILE,
    DEFAULT_PORTFOLIO_ID,
    PCE_PRODUCT,
    PCE_ROLE,
    PCE_SPEC,
    PCE_VERSION,
    PCE_WORKSTREAM_ID,
    POLICY_ENGINE_VERSION,
    VALIDATOR_VERSION,
)
from institutional_policy.validator import validate_assessment

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    policy_history.reset_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PCE_WORKSTREAM_ID,
        "product": PCE_PRODUCT,
        "version": PCE_VERSION,
        "role": PCE_ROLE,
        "llm": False,
        "optimises": False,
        "authoritative_for_cio": True,
        "governs_allocations": True,
        "policy_engine_version": POLICY_ENGINE_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "profiles": list_profiles(),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PCE_SPEC,
        "brand": "AGI",
        "phase": 4,
        "history": policy_history.metrics(),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    latest_rows = []
    for pid in policy_history.metrics().get("portfolios") or []:
        a = policy_history.latest(pid)
        if a:
            latest_rows.append(a)
    top = latest_rows[-1] if latest_rows else None
    out_of_mandate = [
        a.portfolio_id for a in latest_rows if a.overall_status in {"Breach", "Critical Breach"}
    ]
    active_violations = sum(len(a.violations) for a in latest_rows)
    nearing = sum(len(a.nearing_limits) for a in latest_rows)
    return {
        "status": h.get("status"),
        "workstream_id": PCE_WORKSTREAM_ID,
        "product": PCE_PRODUCT,
        "version": PCE_VERSION,
        "llm": False,
        "policy_center": True,
        "policy_assessment": top.to_dict() if top else None,
        "overall_status": top.overall_status if top else None,
        "active_violations": active_violations,
        "compliance_score": top.compliance_score if top else None,
        "new_violations_today": active_violations,  # session-scoped; no durable day clock
        "portfolios_out_of_mandate": list(dict.fromkeys(out_of_mandate)),
        "constraints_nearing_limits": nearing,
        "profile_id": top.profile_id if top else None,
        "assessments_cached": len(latest_rows),
    }


def _load_portfolio(portfolio_id: str) -> tuple[Any, dict[str, Any], list[str]]:
    try:
        from institutional_portfolio.production import get_portfolio_graph
    except Exception as exc:  # noqa: BLE001
        return None, {}, [f"PKG-01 unavailable: {exc}"]

    graph = get_portfolio_graph(portfolio_id, rebuild=True, include_company_graphs=True)
    if not graph.get("ok"):
        return None, graph, list(graph.get("validation_errors") or ["portfolio graph failed"])

    try:
        from institutional_portfolio.production import _GRAPHS

        g = _GRAPHS.get(str(portfolio_id))
        if g and g.institutional_portfolio:
            return g.institutional_portfolio, graph, []
    except Exception:  # noqa: BLE001
        pass

    try:
        from institutional_portfolio.portfolio_entities import (
            AllocationRecord,
            DecisionSummary,
            ExposureRecord,
            HoldingRecord,
            InstitutionalPortfolio,
            RiskRecord,
        )

        raw = graph.get("portfolio") or {}
        holds = tuple(
            HoldingRecord(
                ticker=str(h.get("ticker") or "").upper(),
                company=str(h.get("company") or ""),
                weight=float(h.get("weight") or 0.0),
                market_value=float(h.get("market_value") or 0.0),
                quantity=float(h.get("quantity") or 0.0),
                sector=str(h.get("sector") or ""),
                industry=str(h.get("industry") or ""),
                country=str(h.get("country") or "IN"),
                recommendation=str(h.get("recommendation") or ""),
                confidence=int(h.get("confidence") or 0),
                decision_id=str(h.get("decision_id") or ""),
                company_graph_id=str(h.get("company_graph_id") or ""),
            )
            for h in (raw.get("holdings") or [])
        )
        ip = InstitutionalPortfolio(
            portfolio_id=str(raw.get("portfolio_id") or portfolio_id),
            name=str(raw.get("name") or portfolio_id),
            holdings=holds,
            allocations=tuple(
                AllocationRecord(
                    ticker=str(a.get("ticker") or ""),
                    weight=float(a.get("weight") or 0.0),
                    target_band=str(a.get("target_band") or ""),
                    role=str(a.get("role") or "core"),
                )
                for a in (raw.get("allocations") or [])
            ),
            exposures=tuple(
                ExposureRecord(
                    dimension=str(e.get("dimension") or ""),
                    name=str(e.get("name") or ""),
                    weight=float(e.get("weight") or 0.0),
                )
                for e in (raw.get("exposures") or [])
            ),
            risks=tuple(
                RiskRecord(
                    kind=str(r.get("kind") or ""),
                    label=str(r.get("label") or ""),
                    severity=str(r.get("severity") or ""),
                    score=float(r.get("score") or 0.0),
                    detail=str(r.get("detail") or ""),
                )
                for r in (raw.get("risks") or [])
            ),
            decisions=tuple(
                DecisionSummary(
                    ticker=str(d.get("ticker") or ""),
                    recommendation=str(d.get("recommendation") or ""),
                    confidence=int(d.get("confidence") or 0),
                    decision_id=str(d.get("decision_id") or ""),
                )
                for d in (raw.get("decisions") or [])
            ),
            cash_weight=float(raw.get("cash_weight") or 0.0),
            base_currency=str(raw.get("base_currency") or "INR"),
            graph_id=str(raw.get("graph_id") or graph.get("graph_id") or ""),
            version=str(raw.get("version") or ""),
            as_of=str(raw.get("as_of") or ""),
        )
        return ip, graph, []
    except Exception as exc:  # noqa: BLE001
        return None, graph, [f"portfolio deserialize failed: {exc}"]


def _load_risk(portfolio_id: str) -> Any:
    try:
        from institutional_portfolio_risk.production import evaluate_portfolio_risk, get_risk_object

        payload = evaluate_portfolio_risk({"portfolio_id": portfolio_id})
        if payload.get("ok"):
            return get_risk_object(portfolio_id)
    except Exception:  # noqa: BLE001
        return None
    return None


def check_policy(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": PCE_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["PCE-01 disabled"],
        }

    t0 = time.perf_counter()
    body = dict(payload or {})
    portfolio_id = str(body.get("portfolio_id") or body.get("portfolio") or DEFAULT_PORTFOLIO_ID).strip()
    if portfolio_id in {"default", "DEFAULT"}:
        portfolio_id = DEFAULT_PORTFOLIO_ID
    profile_id = str(
        body.get("policy") or body.get("profile_id") or body.get("profile") or DEFAULT_POLICY_PROFILE
    ).strip()

    ip, _graph, errors = _load_portfolio(portfolio_id)
    if errors or ip is None:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": PCE_WORKSTREAM_ID,
            "validation_errors": errors or ["portfolio unavailable"],
        }

    risk = _load_risk(ip.portfolio_id)
    prev = policy_history.latest(ip.portfolio_id, profile_id)
    assessment = generate_policy_assessment(
        ip,
        profile_id=profile_id,
        portfolio_risk=risk,
        previous_version=prev.policy_version if prev else 0,
    )

    prelim = build_diagnostics(
        assessment,
        latency_ms=(time.perf_counter() - t0) * 1000.0,
        holding_count=len(ip.holdings),
    )
    assessment = replace(assessment, diagnostics=prelim)

    validation = validate_assessment(assessment, holding_count=len(ip.holdings))
    diag = build_diagnostics(
        assessment,
        validation=validation.to_dict(),
        latency_ms=(time.perf_counter() - t0) * 1000.0,
        holding_count=len(ip.holdings),
    )
    assessment = replace(assessment, diagnostics=diag)

    if not validation.ok:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": PCE_WORKSTREAM_ID,
            "validation_errors": list(validation.errors),
            "gates": validation.gates,
            "assessment": assessment.to_dict(),
            "diagnostics": diag,
            "llm": False,
        }

    policy_history.record(assessment)
    return {
        "ok": True,
        "rejected": False,
        "workstream_id": PCE_WORKSTREAM_ID,
        "product": PCE_PRODUCT,
        "version": PCE_VERSION,
        "assessment": assessment.to_dict(),
        "diagnostics": diag,
        "portfolio_graph_id": assessment.portfolio_graph_id,
        "portfolio_risk_id": assessment.portfolio_risk_id,
        "authoritative": True,
        "llm": False,
    }


def get_policy_assessment(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    *,
    profile_id: str = DEFAULT_POLICY_PROFILE,
    refresh: bool = True,
    include_history: bool = False,
) -> dict[str, Any]:
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip()
    if pid in {"default", "DEFAULT"}:
        pid = DEFAULT_PORTFOLIO_ID
    profile = str(profile_id or DEFAULT_POLICY_PROFILE).strip()
    if refresh or policy_history.latest(pid, profile) is None:
        result = check_policy({"portfolio_id": pid, "policy": profile})
        if include_history and result.get("ok"):
            result = dict(result)
            result["history"] = policy_history.list_versions(pid, profile)
        return result
    latest = policy_history.latest(pid, profile)
    assert latest is not None
    out = {
        "ok": True,
        "workstream_id": PCE_WORKSTREAM_ID,
        "assessment": latest.to_dict(),
        "diagnostics": latest.diagnostics,
        "cached": True,
        "authoritative": True,
        "llm": False,
    }
    if include_history:
        out["history"] = policy_history.list_versions(pid, profile)
    return out


def get_assessment_object(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    profile_id: str = DEFAULT_POLICY_PROFILE,
):
    """Return live InstitutionalPolicyAssessment for CIO-01."""
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip()
    if pid in {"default", "DEFAULT"}:
        pid = DEFAULT_PORTFOLIO_ID
    profile = str(profile_id or DEFAULT_POLICY_PROFILE).strip()
    cached = policy_history.latest(pid, profile)
    if cached is not None:
        return cached
    result = check_policy({"portfolio_id": pid, "policy": profile})
    if result.get("ok"):
        return policy_history.latest(pid, profile)
    return None
