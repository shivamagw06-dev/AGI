"""PKG-01 production façades — portfolio graph / InstitutionalPortfolio / Mission Control."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from institutional_portfolio.diagnostics import build_diagnostics, validate_graph
from institutional_portfolio.flags import flags_dict, is_enabled
from institutional_portfolio.fixtures import demo_holdings, demo_portfolio_spec
from institutional_portfolio.portfolio_entities import HoldingRecord
from institutional_portfolio.portfolio_graph import PortfolioKnowledgeGraph, build_portfolio_graph
from institutional_portfolio.schema import (
    DEFAULT_PORTFOLIO_ID,
    PKG_PRODUCT,
    PKG_ROLE,
    PKG_SPEC,
    PKG_SPRINT,
    PKG_VERSION,
    PKG_WORKSTREAM_ID,
    PORTFOLIO_GRAPH_ENGINE_VERSION,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_GRAPHS: dict[str, PortfolioKnowledgeGraph] = {}


def reset_for_tests() -> None:
    _GRAPHS.clear()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PKG_WORKSTREAM_ID,
        "sprint": PKG_SPRINT,
        "product": PKG_PRODUCT,
        "version": PKG_VERSION,
        "role": PKG_ROLE,
        "llm": False,
        "scope": "single_portfolio",
        "optimises": False,
        "graph_engine_version": PORTFOLIO_GRAPH_ENGINE_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PKG_SPEC,
        "brand": "AGI",
        "phase": 4,
        "graphs_cached": sorted(_GRAPHS.keys()),
        "note": (
            "Phase 4.1 Portfolio Knowledge Graph (PKG-01). "
            "Distinct from portfolio_office holdings state service."
        ),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    entity_count = 0
    rel_count = 0
    holding_count = 0
    risk_count = 0
    for g in _GRAPHS.values():
        diag = build_diagnostics(g)
        entity_count += int(diag.get("entity_count") or 0)
        rel_count += int(diag.get("relationship_count") or 0)
        holding_count += int(diag.get("holding_count") or 0)
        risk_count += int(diag.get("risk_count") or 0)
    latest = next(iter(_GRAPHS.values()), None)
    ip = latest.institutional_portfolio if latest else None
    return {
        "status": h.get("status"),
        "workstream_id": PKG_WORKSTREAM_ID,
        "sprint": PKG_SPRINT,
        "product": PKG_PRODUCT,
        "version": PKG_VERSION,
        "llm": False,
        "portfolio_intelligence": True,
        "portfolios_cached": h.get("graphs_cached"),
        "entity_count": entity_count,
        "relationship_count": rel_count,
        "holding_count": holding_count,
        "risk_count": risk_count,
        "sector_exposures": (latest.meta or {}).get("sector_exposures") if latest else [],
        "average_correlation": (latest.meta or {}).get("average_correlation") if latest else None,
        "concentration": (latest.meta or {}).get("concentration") if latest else None,
        "recommendation_mix": (latest.meta or {}).get("recommendation_mix") if latest else [],
        "portfolio_name": ip.name if ip else None,
    }


def _enrich_holding(base: HoldingRecord) -> HoldingRecord:
    """Attach company decision + company graph ids when available."""
    rec = base.recommendation
    conf = base.confidence
    decision_id = base.decision_id
    company_graph_id = base.company_graph_id
    company = base.company
    sector = base.sector
    industry = base.industry

    try:
        from institutional_decision import history as decision_history
        from institutional_decision.production import decide_company

        latest = decision_history.latest(base.ticker)
        if latest is None:
            decide_company(
                {"ticker": base.ticker, "include_calibration": True, "include_drift": False}
            )
            latest = decision_history.latest(base.ticker)
        if latest is not None:
            rec = str(latest.recommendation or rec).upper()
            conf = int(latest.confidence or conf or 0)
            decision_id = str(latest.decision_id or "")
            company_graph_id = str(getattr(latest, "knowledge_graph_id", "") or company_graph_id)
    except Exception:  # noqa: BLE001
        pass

    try:
        from institutional_reporting.fixtures import get_fixture

        fixture = get_fixture(base.ticker)
        if fixture is not None:
            company = str(getattr(fixture, "company_name", None) or company)
            sector = str(getattr(fixture, "sector", None) or sector)
            industry = str(getattr(fixture, "industry", None) or industry or "Private Banks")
    except Exception:  # noqa: BLE001
        pass

    try:
        from institutional_graph.production import get_company_graph

        cg = get_company_graph(base.ticker, include_paths=False, include_inference=True, rebuild=False)
        if cg.get("ok") and cg.get("graph_id"):
            company_graph_id = str(cg.get("graph_id"))
        elif not company_graph_id:
            cg = get_company_graph(
                base.ticker, include_paths=False, include_inference=True, rebuild=True
            )
            if cg.get("ok"):
                company_graph_id = str(cg.get("graph_id") or "")
    except Exception:  # noqa: BLE001
        pass

    return HoldingRecord(
        ticker=base.ticker,
        company=company,
        weight=base.weight,
        market_value=base.market_value,
        quantity=base.quantity,
        sector=sector,
        industry=industry,
        country=base.country,
        recommendation=rec,
        confidence=conf,
        decision_id=decision_id,
        company_graph_id=company_graph_id,
    )


def _holdings_from_portfolio_office(portfolio_id: str) -> Optional[tuple[list[HoldingRecord], dict]]:
    try:
        from portfolio_office import store as pf_store
        from portfolio_office.weights import apply_weights

        raw = pf_store.get_portfolio(portfolio_id)
        if not raw:
            return None
        weighted = apply_weights(raw) if hasattr(apply_weights, "__call__") else raw
        portfolio = weighted if isinstance(weighted, dict) else raw
        holds = []
        for h in portfolio.get("holdings") or []:
            holds.append(
                HoldingRecord(
                    ticker=str(h.get("ticker") or "").upper(),
                    company=str(h.get("company") or h.get("ticker") or ""),
                    weight=float(h.get("weight") or 0.0),
                    market_value=float(h.get("current_market_value") or 0.0),
                    quantity=float(h.get("quantity") or 0.0),
                    sector=str(h.get("sector") or "Unknown"),
                    industry=str(h.get("industry") or "Unknown"),
                    country=str(h.get("country") or "IN"),
                )
            )
        cash = portfolio.get("cash") or {}
        meta = portfolio.get("metadata") or {}
        spec = {
            "portfolio_id": portfolio.get("portfolio_id") or portfolio_id,
            "name": meta.get("name") or portfolio_id,
            "cash_weight": float(cash.get("weight") or 0.0),
            "base_currency": meta.get("base_currency") or "INR",
        }
        return holds, spec
    except Exception:  # noqa: BLE001
        return None


def _resolve_inputs(
    portfolio_id: str,
    *,
    holdings: Optional[Sequence[dict[str, Any]]] = None,
    name: Optional[str] = None,
    cash_weight: Optional[float] = None,
) -> tuple[str, str, list[HoldingRecord], float, str]:
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip() or DEFAULT_PORTFOLIO_ID

    if holdings:
        holds = [
            HoldingRecord(
                ticker=str(h.get("ticker") or "").upper(),
                company=str(h.get("company") or h.get("ticker") or ""),
                weight=float(h.get("weight") or 0.0),
                market_value=float(h.get("market_value") or h.get("current_market_value") or 0.0),
                quantity=float(h.get("quantity") or 0.0),
                sector=str(h.get("sector") or "Unknown"),
                industry=str(h.get("industry") or "Unknown"),
                country=str(h.get("country") or "IN"),
                recommendation=str(h.get("recommendation") or ""),
                confidence=int(h.get("confidence") or 0),
            )
            for h in holdings
            if str(h.get("ticker") or "").strip()
        ]
        return (
            pid,
            name or pid,
            holds,
            float(cash_weight if cash_weight is not None else 0.0),
            "INR",
        )

    office = _holdings_from_portfolio_office(pid)
    if office is not None:
        holds, spec = office
        return (
            str(spec.get("portfolio_id") or pid),
            name or str(spec.get("name") or pid),
            holds,
            float(cash_weight if cash_weight is not None else spec.get("cash_weight") or 0.0),
            str(spec.get("base_currency") or "INR"),
        )

    # Default demo Investment Office book
    demo = demo_portfolio_spec()
    return (
        str(demo["portfolio_id"]),
        name or str(demo["name"]),
        demo_holdings(),
        float(cash_weight if cash_weight is not None else demo["cash_weight"]),
        str(demo["base_currency"]),
    )


def build_portfolio_knowledge_graph(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    *,
    holdings: Optional[Sequence[dict[str, Any]]] = None,
    name: Optional[str] = None,
    cash_weight: Optional[float] = None,
    enrich: bool = True,
) -> PortfolioKnowledgeGraph:
    pid, pname, holds, cash_w, ccy = _resolve_inputs(
        portfolio_id, holdings=holdings, name=name, cash_weight=cash_weight
    )
    if enrich:
        holds = [_enrich_holding(h) for h in holds]
    graph = build_portfolio_graph(
        portfolio_id=pid,
        name=pname,
        holdings=holds,
        cash_weight=cash_w,
        base_currency=ccy,
    )
    _GRAPHS[pid] = graph
    return graph


def _serialize(
    graph: PortfolioKnowledgeGraph,
    *,
    include_company_graphs: bool = False,
) -> dict[str, Any]:
    diagnostics = build_diagnostics(graph)
    errors = validate_graph(graph)
    payload = graph.to_dict()
    out: dict[str, Any] = {
        "ok": not errors,
        "rejected": bool(errors),
        "workstream_id": PKG_WORKSTREAM_ID,
        "sprint": PKG_SPRINT,
        "product": PKG_PRODUCT,
        "version": PKG_VERSION,
        "validation_errors": errors,
        "diagnostics": diagnostics,
        "llm": False,
        **payload,
    }
    # Flatten institutional portfolio for convenient clients
    if graph.institutional_portfolio:
        out["portfolio"] = graph.institutional_portfolio.to_dict()
        out["holdings"] = [h.to_dict() for h in graph.institutional_portfolio.holdings]
        out["allocations"] = [a.to_dict() for a in graph.institutional_portfolio.allocations]
        out["exposures"] = [e.to_dict() for e in graph.institutional_portfolio.exposures]
        out["risks"] = [r.to_dict() for r in graph.institutional_portfolio.risks]
        out["decisions"] = [d.to_dict() for d in graph.institutional_portfolio.decisions]
    out["concentration"] = (graph.meta or {}).get("concentration")
    out["correlations"] = {
        "average": (graph.meta or {}).get("average_correlation"),
        "count": (graph.meta or {}).get("correlation_count"),
    }
    if include_company_graphs:
        linked = {}
        for h in graph.institutional_portfolio.holdings if graph.institutional_portfolio else ():
            if h.company_graph_id:
                linked[h.ticker] = h.company_graph_id
        out["company_graphs"] = linked
    return out


def get_portfolio_graph(
    portfolio_id: str = DEFAULT_PORTFOLIO_ID,
    *,
    rebuild: bool = True,
    include_company_graphs: bool = True,
) -> dict[str, Any]:
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": PKG_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["PKG-01 disabled"],
        }
    pid = str(portfolio_id or DEFAULT_PORTFOLIO_ID).strip() or DEFAULT_PORTFOLIO_ID
    if rebuild or pid not in _GRAPHS:
        graph = build_portfolio_knowledge_graph(pid)
    else:
        graph = _GRAPHS[pid]
    return _serialize(graph, include_company_graphs=include_company_graphs)


def portfolio_graph_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    portfolio_id = str(body.get("portfolio_id") or DEFAULT_PORTFOLIO_ID)
    return get_portfolio_graph(
        portfolio_id,
        rebuild=True,
        include_company_graphs=bool(body.get("include_company_graphs", True)),
    )


def get_institutional_portfolio(portfolio_id: str = DEFAULT_PORTFOLIO_ID) -> dict[str, Any]:
    result = get_portfolio_graph(portfolio_id, rebuild=True, include_company_graphs=True)
    if not result.get("ok"):
        return result
    return {
        "ok": True,
        "workstream_id": PKG_WORKSTREAM_ID,
        "sprint": PKG_SPRINT,
        "portfolio": result.get("portfolio"),
        "graph_id": result.get("graph_id"),
        "concentration": result.get("concentration"),
        "correlations": result.get("correlations"),
        "diagnostics": result.get("diagnostics"),
        "llm": False,
    }
