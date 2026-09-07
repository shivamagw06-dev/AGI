"""Internal HIP / HAP / HKO APIs — historical retrieval never hits external providers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.hri.engine import HistoricalRelationshipEngine
from app.timeline.builder import TimelineBuilder

router = APIRouter()


def _state(request: Request):
    return request.app.state


@router.get("/healthz")
def healthz(request: Request) -> dict:
    settings = _state(request).settings
    return {"status": "ok", "service": settings.service_name, "version": settings.version}


@router.get("/readyz")
def readyz(request: Request) -> dict:
    store = _state(request).store
    return {
        "status": "ready",
        "raw_archive": store.count_raw(),
        "historical_objects": store.count_objects(),
        "timeline_events": store.count_timeline_events(),
        "relationships": store.count_relationships(published_only=True),
    }


# ----- Sprint 8.2 History / Timeline Intelligence -----


@router.get("/v1/history/company/{symbol}")
def history_company(symbol: str, request: Request) -> dict:
    return _state(request).gateway.company_history(symbol)


# Static timeline paths must precede /timeline/{symbol}
@router.get("/v1/history/timeline/sector/{sector}")
def history_sector_timeline(sector: str, request: Request) -> dict:
    return _state(request).gateway.sector_timeline(sector)


@router.get("/v1/history/timeline/market")
def history_market_timeline(request: Request) -> dict:
    return _state(request).gateway.market_timeline()


@router.get("/v1/history/timeline/macro")
def history_macro_timeline(request: Request) -> dict:
    return _state(request).gateway.macro_timeline()


@router.get("/v1/history/timeline/{symbol}")
def history_timeline(symbol: str, request: Request) -> dict:
    return _state(request).gateway.timeline(symbol)


@router.get("/v1/history/financials/{symbol}")
def history_financials(symbol: str, request: Request, period_kind: str | None = None) -> dict:
    return {
        "company_symbol": symbol.upper(),
        "items": _state(request).gateway.financials(symbol, period_kind=period_kind),
        "providers_queried": [],
    }


@router.get("/v1/history/events/{symbol}")
def history_events(symbol: str, request: Request) -> dict:
    return {
        "company_symbol": symbol.upper(),
        "items": _state(request).gateway.events(symbol),
        "providers_queried": [],
    }


class CompareRequest(BaseModel):
    symbol: str = Field(..., examples=["INFY"])
    as_of_period: str = Field(default="FY2018", examples=["FY2018"])
    include_current_tip: bool = True


@router.post("/v1/history/compare")
def history_compare(body: CompareRequest, request: Request) -> dict:
    return _state(request).gateway.compare(
        body.symbol,
        as_of_period=body.as_of_period,
        include_current_tip=body.include_current_tip,
    )


@router.get("/v1/history/mission-control")
def history_mission_control(request: Request) -> dict:
    return _state(request).gateway.mission_control()


# ----- Sprint 8.3 Historical Relationship Intelligence -----


@router.get("/v1/history/relationships/company/{symbol}")
def history_relationships_company(symbol: str, request: Request) -> dict:
    return _state(request).gateway.relationships.company_relationships(symbol)


@router.get("/v1/history/relationships/sector/{sector}")
def history_relationships_sector(sector: str, request: Request) -> dict:
    return _state(request).gateway.relationships.sector_relationships(sector)


@router.get("/v1/history/relationships/macro/{event}")
def history_relationships_macro(event: str, request: Request) -> dict:
    return _state(request).gateway.relationships.macro_relationships(event)


@router.get("/v1/history/relationships/market")
def history_relationships_market(request: Request) -> dict:
    return _state(request).gateway.relationships.market_relationships()


class ExplainRelationshipRequest(BaseModel):
    source: str = Field(..., examples=["RBI Rate Cut"])
    target: str = Field(..., examples=["HDFCBANK"])


@router.post("/v1/history/relationships/explain")
def history_relationships_explain(body: ExplainRelationshipRequest, request: Request) -> dict:
    """Success path: How have RBI rate cuts historically affected HDFC Bank?"""
    return _state(request).gateway.relationships.explain(source=body.source, target=body.target)


# ----- Sprint 8.4 Historical Analogue Intelligence -----


@router.get("/v1/history/analogues/company/{symbol}")
def history_analogues_company(
    symbol: str,
    request: Request,
    question: str | None = None,
    as_of_period: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> dict:
    return _state(request).gateway.analogues.company_analogues(
        symbol,
        question=question,
        as_of_period=as_of_period,
        situation=situation,
        top_k=top_k,
    )


@router.get("/v1/history/analogues/sector/{sector}")
def history_analogues_sector(
    sector: str,
    request: Request,
    question: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> dict:
    return _state(request).gateway.analogues.sector_analogues(
        sector, question=question, situation=situation, top_k=top_k
    )


@router.get("/v1/history/analogues/market")
def history_analogues_market(
    request: Request,
    question: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> dict:
    return _state(request).gateway.analogues.market_analogues(
        question=question, situation=situation, top_k=top_k
    )


@router.get("/v1/history/analogues/macro")
def history_analogues_macro(
    request: Request,
    question: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> dict:
    return _state(request).gateway.analogues.macro_analogues(
        question=question, situation=situation, top_k=top_k
    )


class AnalogueSearchRequest(BaseModel):
    scope: str = Field(..., examples=["company"])
    entity: str | None = Field(default=None, examples=["INFY"])
    question: str | None = Field(
        default=None, examples=["Has Infosys experienced this type of slowdown before?"]
    )
    situation: str | None = None
    as_of_period: str | None = None
    top_k: int = 5
    features: dict[str, float] | None = None


@router.post("/v1/history/analogues/search")
def history_analogues_search(body: AnalogueSearchRequest, request: Request) -> dict:
    """Success path: Has Infosys experienced this type of slowdown before?"""
    return _state(request).gateway.analogues.search(
        scope=body.scope,
        entity=body.entity,
        question=body.question,
        situation=body.situation,
        as_of_period=body.as_of_period,
        top_k=body.top_k,
        features=body.features,
    )


# ----- Sprint 8.1 legacy historical paths -----


@router.get("/v1/historical/coverage/policy")
def coverage_policy(request: Request) -> dict:
    return _state(request).gateway.policy()


@router.get("/v1/historical/coverage/{symbol}")
def coverage(symbol: str, request: Request) -> dict:
    return _state(request).gateway.coverage(symbol)


@router.get("/v1/historical/company/{symbol}")
def company_history(symbol: str, request: Request) -> dict:
    return _state(request).gateway.company_history(symbol)


@router.get("/v1/historical/company/{symbol}/prices")
def company_prices(symbol: str, request: Request, period_kind: str = "daily") -> dict:
    rows = _state(request).store.list_prices(symbol, period_kind=period_kind)
    return {"company_symbol": symbol.upper(), "period_kind": period_kind, "items": rows, "providers_queried": []}


@router.get("/v1/historical/company/{symbol}/financials")
def company_financials(symbol: str, request: Request, period_kind: str | None = None) -> dict:
    rows = _state(request).gateway.financials(symbol, period_kind=period_kind)
    return {"company_symbol": symbol.upper(), "items": rows, "providers_queried": []}


@router.get("/v1/historical/company/{symbol}/revenue")
def company_revenue(
    symbol: str,
    request: Request,
    from_period: str = "FY2015",
    to_period: str = "FY2025",
) -> dict:
    """Success path: revenue growth + valuation across earnings cycles from store only."""
    return _state(request).gateway.revenue_growth(
        symbol, from_period=from_period, to_period=to_period
    )


@router.get("/v1/historical/company/{symbol}/events")
def company_events(symbol: str, request: Request) -> dict:
    return {
        "company_symbol": symbol.upper(),
        "items": _state(request).gateway.events(symbol),
        "providers_queried": [],
    }


@router.get("/v1/historical/company/{symbol}/actions")
def company_actions(symbol: str, request: Request) -> dict:
    return {
        "company_symbol": symbol.upper(),
        "items": _state(request).store.list_actions(symbol),
        "providers_queried": [],
    }


@router.get("/v1/historical/company/{symbol}/reports")
def company_reports(symbol: str, request: Request) -> dict:
    return {
        "company_symbol": symbol.upper(),
        "items": _state(request).store.list_reports(symbol),
        "providers_queried": [],
    }


@router.get("/v1/historical/company/{symbol}/entity")
def company_entity(symbol: str, request: Request) -> dict:
    entity = _state(request).store.get_entity(symbol)
    if not entity:
        raise HTTPException(status_code=404, detail="entity_not_found")
    return {"company_symbol": symbol.upper(), "entity": entity}


@router.get("/v1/internal/runs")
def list_runs(request: Request) -> dict:
    return {"runs": _state(request).store.list_runs()}


class BootstrapRequest(BaseModel):
    symbols: list[str] | None = None
    collectors: list[str] | None = None
    rebuild_timelines: bool = True
    rebuild_relationships: bool = True


@router.post("/v1/internal/bootstrap")
def bootstrap(request: Request, body: BootstrapRequest | None = None) -> dict:
    """Ops-only: bulk historical bootstrap + timeline + relationship rebuild. Never called by Ask."""
    payload = body or BootstrapRequest()
    state = _state(request)
    collectors = state.collectors
    if payload.collectors:
        collectors = {k: v for k, v in collectors.items() if k in payload.collectors}
    symbols = payload.symbols or list(state.settings.watchlist)
    summary = state.pipeline.bootstrap_all(collectors, symbols=symbols)
    timelines = None
    relationships = None
    if payload.rebuild_timelines:
        builder = TimelineBuilder(state.store)
        timelines = builder.rebuild_all(symbols)
    if payload.rebuild_relationships:
        relationships = HistoricalRelationshipEngine(state.store).rebuild_all(symbols)
    return {
        "status": "ok",
        "summary": summary,
        "timelines": timelines,
        "relationships": relationships,
        "raw_archive": state.store.count_raw(),
        "historical_objects": state.store.count_objects(),
        "timeline_events": state.store.count_timeline_events(),
        "relationship_count": state.store.count_relationships(published_only=True),
    }


@router.post("/v1/internal/timelines/rebuild")
def rebuild_timelines(request: Request, body: BootstrapRequest | None = None) -> dict:
    """Ops-only: regenerate company/sector/market/macro timelines from HKO + seeds."""
    state = _state(request)
    payload = body or BootstrapRequest()
    symbols = payload.symbols or list(state.settings.watchlist)
    out = TimelineBuilder(state.store).rebuild_all(symbols)
    return {"status": "ok", "timelines": out, "timeline_events": state.store.count_timeline_events()}


@router.post("/v1/internal/relationships/rebuild")
def rebuild_relationships(request: Request, body: BootstrapRequest | None = None) -> dict:
    """Ops-only: regenerate evidence-backed historical relationship graph."""
    state = _state(request)
    payload = body or BootstrapRequest()
    symbols = payload.symbols or list(state.settings.watchlist)
    # Ensure timelines exist before deriving edges
    TimelineBuilder(state.store).rebuild_all(symbols)
    out = HistoricalRelationshipEngine(state.store).rebuild_all(symbols)
    return {
        "status": "ok",
        "relationships": out,
        "relationship_count": state.store.count_relationships(published_only=True),
    }


@router.post("/v1/internal/run/{collector_id}")
def run_collector(collector_id: str, request: Request) -> dict:
    state = _state(request)
    collector = state.collectors.get(collector_id)
    if not collector:
        raise HTTPException(status_code=404, detail="collector_not_found")
    result = state.pipeline.run_collector(collector, mode="bootstrap")
    return {
        "collector_id": collector_id,
        "run_id": result.run_id,
        "accepted": len(result.accepted),
        "rejected": len(result.rejected),
        "duplicates": len(result.duplicates),
        "objects": len(result.objects),
    }
