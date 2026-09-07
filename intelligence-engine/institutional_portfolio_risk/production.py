"""PRE-01 production façades — evaluate portfolio risk / Mission Control Risk Center."""

from __future__ import annotations

import time
from dataclasses import replace
from typing import Any, Optional

from institutional_portfolio_risk.diagnostics import build_diagnostics
from institutional_portfolio_risk.flags import flags_dict, is_enabled
from institutional_portfolio_risk import history as risk_history
from institutional_portfolio_risk.risk_engine import generate_portfolio_risk
from institutional_portfolio_risk.schema import (
    DEFAULT_PORTFOLIO_ID,
    PRE_PRODUCT,
    PRE_ROLE,
    PRE_SPEC,
    PRE_VERSION,
    PRE_WORKSTREAM_ID,
    RISK_ENGINE_VERSION,
    VALIDATOR_VERSION,
)
from institutional_portfolio_risk.validator import validate_risk

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    risk_history.reset_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PRE_WORKSTREAM_ID,
        "product": PRE_PRODUCT,
        "version": PRE_VERSION,
        "role": PRE_ROLE,
        "llm": False,
        "monte_carlo": False,
        "var": False,
        "optimises": False,
        "authoritative_for_cio": True,
        "risk_engine_version": RISK_ENGINE_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PRE_SPEC,
        "brand": "AGI",
        "phase": 4,
        "history": risk_history.metrics(),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    latest_rows = []
    for pid in risk_history.metrics().get("portfolios") or []:
        r = risk_history.latest(pid)
        if r:
            latest_rows.append(r)
    top = latest_rows[-1] if latest_rows else None
    worst_stress = None
    if top and top.stress_results:
        worst_stress = min(top.stress_results, key=lambda s: s.portfolio_impact_pct)
    return {
        "status": h.get("status"),
        "workstream_id": PRE_WORKSTREAM_ID,
        "product": PRE_PRODUCT,
        "version": PRE_VERSION,
        "llm": False,
        "risk_center": True,
        "portfolio_risk": top.to_dict() if top else None,
        "overall_risk": top.overall_risk if top else None,
        "highest_concentration": (
            {
                "ticker": top.concentration.largest_position_ticker,
                "weight": top.concentration.largest_position_weight,
                "level": top.concentration.level,
                "top_sector": top.concentration.top_sector,
                "sector_concentration": top.concentration.sector_concentration,
            }
            if top
            else None
        ),
        "liquidity_warning": (
            top.liquidity.level in {"High", "Critical"} if top else False
        ),
        "liquidity_level": top.liquidity.level if top else None,
        "stress_impact": worst_stress.to_dict() if worst_stress else None,
        "correlation_drift": (
            {
                "level": top.correlations.level,
                "average_correlation": top.correlations.average_correlation,
                "max_pair_correlation": top.correlations.max_pair_correlation,
            }
            if top
            else None
        ),
        "coverage": top.scorecard.coverage if top and top.scorecard else None,
        "warning_count": len(top.warnings) if top else 0,
        "risks_cached": len(latest_rows),
    }


def _load_portfolio(portfolio_id: str) -> tuple[Any, dict[str, Any], list[str]]:
    """Load InstitutionalPortfolio via PKG-01."""
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


def evaluate_portfolio_risk(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": PRE_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["PRE-01 disabled"],
        }

    t0 = time.perf_counter()
    body = dict(payload or {})
    portfolio_id = str(body.get("portfolio_id") or body.get("portfolio") or DEFAULT_PORTFOLIO_ID).strip()
    if portfolio_id in {"default", "DEFAULT"}:
        portfolio_id = DEFAULT_PORTFOLIO_ID

    ip, _graph_payload, errors = _load_portfolio(portfolio_id)
    if errors or ip is None:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": PRE_WORKSTREAM_ID,
            "validation_errors": errors or ["portfolio unavailable"],
        }

    prev = risk_history.latest(ip.portfolio_id)
    risk = generate_portfolio_risk(
        ip,
        previous_version=prev.risk_version if prev else 0,
    )

    prelim_diag = build_diagnostics(
        risk,
        latency_ms=(time.perf_counter() - t0) * 1000.0,
        holding_count=len(ip.holdings),
    )
    risk = replace(risk, diagnostics=prelim_diag)

    validation = validate_risk(risk, holding_count=len(ip.holdings))
    diag = build_diagnostics(
        risk,
        validation=validation.to_dict(),
        latency_ms=(time.perf_counter() - t0) * 1000.0,
        holding_count=len(ip.holdings),
    )
    risk = replace(risk, diagnostics=diag)

    if not validation.ok:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": PRE_WORKSTREAM_ID,
            "validation_errors": list(validation.errors),
            "gates": validation.gates,
            "risk": risk.to_dict(),
            "diagnostics": diag,
            "llm": False,
        }

    risk_history.record(risk)
    return {
        "ok": True,
        "rejected": False,
        "workstream_id": PRE_WORKSTREAM_ID,
        "product": PRE_PRODUCT,
        "version": PRE_VERSION,
        "risk": risk.to_dict(),
        "diagnostics": diag,
        "portfolio_graph_id": risk.portfolio_graph_id,
        "authoritative": True,
        "llm": False,
    }


def get_portfolio_risk(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    *,
    refresh: bool = True,
    include_history: bool = False,
) -> dict[str, Any]:
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip()
    if pid in {"default", "DEFAULT"}:
        pid = DEFAULT_PORTFOLIO_ID
    if refresh or risk_history.latest(pid) is None:
        result = evaluate_portfolio_risk({"portfolio_id": pid})
        if include_history and result.get("ok"):
            result = dict(result)
            result["history"] = risk_history.list_versions(pid)
        return result
    latest = risk_history.latest(pid)
    assert latest is not None
    out = {
        "ok": True,
        "workstream_id": PRE_WORKSTREAM_ID,
        "risk": latest.to_dict(),
        "diagnostics": latest.diagnostics,
        "cached": True,
        "authoritative": True,
        "llm": False,
    }
    if include_history:
        out["history"] = risk_history.list_versions(pid)
    return out


def get_risk_object(portfolio_id: str = DEFAULT_PORTFOLIO_ID):
    """Return live InstitutionalPortfolioRisk (evaluate if needed) for CIO-01."""
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip()
    if pid in {"default", "DEFAULT"}:
        pid = DEFAULT_PORTFOLIO_ID
    cached = risk_history.latest(pid)
    if cached is not None:
        return cached
    result = evaluate_portfolio_risk({"portfolio_id": pid})
    if result.get("ok"):
        return risk_history.latest(pid)
    return None
