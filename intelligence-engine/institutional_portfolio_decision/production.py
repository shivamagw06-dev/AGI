"""CIO-01 production façades — portfolio decide / Mission Control Portfolio Command Center."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Optional

from institutional_portfolio_decision.decision_engine import generate_portfolio_decision
from institutional_portfolio_decision.decision_validator import validate_decision
from institutional_portfolio_decision.diagnostics import build_diagnostics
from institutional_portfolio_decision.flags import flags_dict, is_enabled
from institutional_portfolio_decision import history as decision_history
from institutional_portfolio_decision.schema import (
    CIO_PRODUCT,
    CIO_ROLE,
    CIO_SPEC,
    CIO_VERSION,
    CIO_WORKSTREAM_ID,
    DECISION_ENGINE_VERSION,
    DEFAULT_PORTFOLIO_ID,
    VALIDATOR_VERSION,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    decision_history.reset_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": CIO_WORKSTREAM_ID,
        "product": CIO_PRODUCT,
        "version": CIO_VERSION,
        "role": CIO_ROLE,
        "llm": False,
        "mutates_company_decisions": False,
        "referential_company_decisions": True,
        "consumes_pre01": True,
        "consumes_pce01": True,
        "optimises": False,
        "executes_trades": False,
        "decision_engine_version": DECISION_ENGINE_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": CIO_SPEC,
        "brand": "AGI",
        "phase": 4,
        "history": decision_history.metrics(),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    latest_rows = []
    for pid in decision_history.metrics().get("portfolios") or []:
        d = decision_history.latest(pid)
        if d:
            latest_rows.append(d)
    critical_holdings = []
    for d in latest_rows:
        if d.monitoring_plan:
            critical_holdings.extend(d.monitoring_plan.high_priority_holdings)
    alloc_drift = sum(len(d.allocation_actions) for d in latest_rows)
    exp_drift = sum(
        1
        for d in latest_rows
        for a in d.exposure_actions
        if a.action in {"Reduce", "Increase", "Diversify"}
    )
    upcoming = []
    for d in latest_rows:
        if d.monitoring_plan:
            upcoming.extend(d.monitoring_plan.required_reviews)
    top = latest_rows[-1] if latest_rows else None
    return {
        "status": h.get("status"),
        "workstream_id": CIO_WORKSTREAM_ID,
        "product": CIO_PRODUCT,
        "version": CIO_VERSION,
        "llm": False,
        "portfolio_command_center": True,
        "portfolio_decision": top.to_dict() if top else None,
        "allocation_drift": alloc_drift,
        "exposure_drift": exp_drift,
        "critical_holdings": list(dict.fromkeys(critical_holdings))[:12],
        "upcoming_reviews": list(dict.fromkeys(upcoming))[:12],
        "scenario_impact": (
            list(top.monitoring_plan.scenario_reruns) if top and top.monitoring_plan else []
        ),
        "decisions_cached": len(latest_rows),
    }


def _load_portfolio(portfolio_id: str) -> tuple[Any, dict[str, Any], list[str]]:
    """Load InstitutionalPortfolio via PKG-01 — company decisions remain referential."""
    try:
        from institutional_portfolio.production import get_portfolio_graph
    except Exception as exc:  # noqa: BLE001
        return None, {}, [f"PKG-01 unavailable: {exc}"]

    graph = get_portfolio_graph(portfolio_id, rebuild=True, include_company_graphs=True)
    if not graph.get("ok"):
        return None, graph, list(graph.get("validation_errors") or ["portfolio graph failed"])

    # Prefer live object from cache
    try:
        from institutional_portfolio.production import _GRAPHS

        g = _GRAPHS.get(str(portfolio_id))
        if g and g.institutional_portfolio:
            return g.institutional_portfolio, graph, []
    except Exception:  # noqa: BLE001
        pass

    # Reconstruct from serialized portfolio dict
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


def decide_portfolio(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": CIO_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["CIO-01 disabled"],
        }

    t0 = time.perf_counter()
    body = dict(payload or {})
    portfolio_id = str(body.get("portfolio_id") or body.get("portfolio") or DEFAULT_PORTFOLIO_ID).strip()
    if portfolio_id in {"default", "DEFAULT"}:
        portfolio_id = DEFAULT_PORTFOLIO_ID

    ip, graph_payload, errors = _load_portfolio(portfolio_id)
    if errors or ip is None:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": CIO_WORKSTREAM_ID,
            "validation_errors": errors or ["portfolio unavailable"],
        }

    # Architectural invariant: never call decide_company to overwrite recommendations
    # for portfolio purposes — PKG-01 already attached referential company decisions.
    # PRE-01 is authoritative for risk; PCE-01 for mandate compliance; CIO-01 consumes both.
    portfolio_risk = None
    try:
        from institutional_portfolio_risk.production import evaluate_portfolio_risk, get_risk_object

        risk_payload = evaluate_portfolio_risk({"portfolio_id": ip.portfolio_id})
        if risk_payload.get("ok"):
            portfolio_risk = get_risk_object(ip.portfolio_id)
    except Exception:  # noqa: BLE001
        portfolio_risk = None

    policy_assessment = None
    try:
        from institutional_policy.production import check_policy, get_assessment_object
        from institutional_policy.schema import DEFAULT_POLICY_PROFILE

        profile = str(body.get("policy") or body.get("profile_id") or DEFAULT_POLICY_PROFILE)
        policy_payload = check_policy({"portfolio_id": ip.portfolio_id, "policy": profile})
        if policy_payload.get("ok"):
            policy_assessment = get_assessment_object(ip.portfolio_id, profile)
    except Exception:  # noqa: BLE001
        policy_assessment = None

    prev = decision_history.latest(ip.portfolio_id)
    decision = generate_portfolio_decision(
        ip,
        previous_version=prev.decision_version if prev else 0,
        concentration=graph_payload.get("concentration") or {},
        portfolio_risk=portfolio_risk,
        policy_assessment=policy_assessment,
        observation_health=float(body.get("observation_health") or 0.7),
        forecast_stability=float(body.get("forecast_stability") or 0.7),
    )

    # Attach diagnostics before validation (gate requires diagnostics)
    prelim_diag = build_diagnostics(decision, latency_ms=(time.perf_counter() - t0) * 1000.0)
    decision = replace(decision, diagnostics=prelim_diag)

    validation = validate_decision(decision, holding_count=len(ip.holdings))
    diag = build_diagnostics(
        decision,
        validation=validation.to_dict(),
        latency_ms=(time.perf_counter() - t0) * 1000.0,
    )
    decision = replace(decision, diagnostics=diag)

    if not validation.ok:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": CIO_WORKSTREAM_ID,
            "validation_errors": list(validation.errors),
            "gates": validation.gates,
            "decision": decision.to_dict(),
            "diagnostics": diag,
            "llm": False,
            "mutates_company_decisions": False,
        }

    decision_history.record(decision)
    return {
        "ok": True,
        "rejected": False,
        "workstream_id": CIO_WORKSTREAM_ID,
        "product": CIO_PRODUCT,
        "version": CIO_VERSION,
        "decision": decision.to_dict(),
        "diagnostics": diag,
        "portfolio_graph_id": decision.portfolio_graph_id,
        "company_decisions_immutable": True,
        "llm": False,
        "mutates_company_decisions": False,
    }


def get_portfolio_decision(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    *,
    refresh: bool = True,
    include_history: bool = False,
) -> dict[str, Any]:
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip()
    if pid in {"default", "DEFAULT"}:
        pid = DEFAULT_PORTFOLIO_ID
    if refresh or decision_history.latest(pid) is None:
        result = decide_portfolio({"portfolio_id": pid})
        if include_history and result.get("ok"):
            result = dict(result)
            result["history"] = decision_history.list_versions(pid)
        return result
    latest = decision_history.latest(pid)
    assert latest is not None
    out = {
        "ok": True,
        "workstream_id": CIO_WORKSTREAM_ID,
        "decision": latest.to_dict(),
        "diagnostics": latest.diagnostics,
        "cached": True,
        "llm": False,
        "mutates_company_decisions": False,
    }
    if include_history:
        out["history"] = decision_history.list_versions(pid)
    return out
