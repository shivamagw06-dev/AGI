"""Internal KAIP APIs — Institutional Knowledge Objects + KRIG. No public endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.contracts.iko import company_knowledge_view
from app.contracts.models import KnowledgeObjectType, Source

router = APIRouter()


class BundleRequest(BaseModel):
    question: str | None = None
    symbols: list[str] | None = None
    sector_key: str | None = None
    query_type: str | None = None
    use_cache: bool = True


class CompareRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    question: str | None = None


def _app_state(request: Request):
    return request.app.state


@router.get("/healthz")
def healthz(request: Request) -> dict:
    settings = _app_state(request).settings
    return {"status": "ok", "service": settings.service_name, "version": settings.version}


@router.get("/readyz")
def readyz(request: Request) -> dict:
    store = _app_state(request).store
    return {
        "status": "ready",
        "raw_events": store.count_raw_events(),
        "published_knowledge_objects": store.count_published_kos(),
    }


@router.get("/v1/knowledge/company/{symbol}")
def get_company(symbol: str, request: Request) -> dict:
    profile = _app_state(request).store.get_company_profile(symbol)
    if not profile:
        raise HTTPException(status_code=404, detail="company_profile_not_found")
    meta = profile.get("metadata") or {}
    source = Source(meta["source"]) if meta.get("source") in {s.value for s in Source} else Source.DERIVED
    view = company_knowledge_view(profile["knowledge"], source=source, version=int(profile["version"]))
    return {
        "object_type": "CompanyProfile",
        **profile,
        "company_knowledge": view.get("CompanyKnowledge"),
    }


@router.get("/v1/knowledge/company/{symbol}/versions")
def get_company_versions(symbol: str, request: Request) -> dict:
    versions = _app_state(request).store.list_versions(KnowledgeObjectType.COMPANY_PROFILE, symbol)
    return {"object_type": "CompanyProfile", "company_symbol": symbol.upper(), "versions": versions}


@router.get("/v1/knowledge/market/{symbol}")
def get_market(symbol: str, request: Request) -> dict:
    snap = _app_state(request).store.get_latest_market(symbol)
    if not snap:
        raise HTTPException(status_code=404, detail="market_snapshot_not_found")
    return {"object_type": "MarketSnapshot", **snap}


@router.get("/v1/knowledge/events/{symbol}")
def get_events(symbol: str, request: Request) -> dict:
    events = _app_state(request).store.list_events(symbol)
    return {"object_type": "CorporateEvent", "company_symbol": symbol.upper(), "items": events}


@router.get("/v1/knowledge/financials/{symbol}")
def get_financials(symbol: str, request: Request) -> dict:
    items = _app_state(request).store.list_financials(symbol)
    return {"object_type": "FinancialStatement", "company_symbol": symbol.upper(), "items": items}


@router.get("/v1/knowledge/learning/{symbol}")
def get_learning(symbol: str, request: Request) -> dict:
    items = _app_state(request).store.list_learning(symbol)
    return {"company_symbol": symbol.upper(), "items": items}


@router.get("/v1/knowledge/memory/{symbol}")
def get_memory(symbol: str, request: Request) -> dict:
    items = _app_state(request).store.list_memory(symbol)
    return {"company_symbol": symbol.upper(), "items": items}


@router.get("/v1/knowledge/timeline/{symbol}")
def get_timeline(symbol: str, request: Request) -> dict:
    items = _app_state(request).store.list_timeline(symbol)
    return {"company_symbol": symbol.upper(), "items": items}


@router.get("/v1/knowledge/conflicts/{symbol}")
def get_conflicts(symbol: str, request: Request) -> dict:
    items = _app_state(request).store.list_conflicts(symbol)
    return {"company_symbol": symbol.upper(), "items": items}


@router.get("/v1/knowledge/sector-learning/{sector_key}")
def get_sector_learning(sector_key: str, request: Request) -> dict:
    items = _app_state(request).store.list_sector_learning(sector_key)
    return {"sector_key": sector_key, "items": items}


@router.get("/v1/knowledge/market-learning")
def get_market_learning(request: Request) -> dict:
    items = _app_state(request).store.list_market_learning()
    return {"items": items}


@router.get("/v1/knowledge/sector/{sector_key}")
def get_sector(sector_key: str, request: Request) -> dict:
    item = _app_state(request).store.get_sector_knowledge(sector_key)
    if not item:
        raise HTTPException(status_code=404, detail="sector_knowledge_not_found")
    return {"object_type": "SectorKnowledge", **item}


@router.get("/v1/knowledge/market-regime/{market_key}")
def get_market_knowledge(market_key: str, request: Request) -> dict:
    item = _app_state(request).store.get_market_knowledge(market_key)
    if not item:
        raise HTTPException(status_code=404, detail="market_knowledge_not_found")
    return {"object_type": "MarketKnowledge", **item}


@router.get("/v1/knowledge/relationships/{symbol}")
def get_relationships(symbol: str, request: Request) -> dict:
    edges = _app_state(request).store.list_relationships("Company", symbol.upper())
    entity = _app_state(request).store.get_entity(symbol)
    return {
        "company_symbol": symbol.upper(),
        "entity": entity.model_dump() if entity else None,
        "edges": edges,
    }


# ----- Sprint 6.4 KRIG -----

@router.post("/v1/knowledge/bundle")
def post_bundle(request: Request, body: BundleRequest | None = None) -> dict:
    """Assemble a Knowledge Bundle by retrieval policy."""
    payload = body or BundleRequest()
    gateway = _app_state(request).gateway
    bundle = gateway.retrieve(
        question=payload.question,
        symbols=payload.symbols,
        sector_key=payload.sector_key,
        query_type=payload.query_type,
        use_cache=payload.use_cache,
    )
    return bundle.to_public_dict()


@router.get("/v1/knowledge/bundle/company/{symbol}")
def get_company_bundle(symbol: str, request: Request, question: str | None = None) -> dict:
    gateway = _app_state(request).gateway
    return gateway.company_bundle(symbol, question=question).to_public_dict()


@router.get("/v1/knowledge/bundle/sector/{sector_key}")
def get_sector_bundle(sector_key: str, request: Request, question: str | None = None) -> dict:
    gateway = _app_state(request).gateway
    return gateway.sector_bundle(sector_key, question=question).to_public_dict()


@router.get("/v1/knowledge/macro")
def get_macro_bundle(request: Request, question: str | None = None) -> dict:
    gateway = _app_state(request).gateway
    return gateway.macro_bundle(question=question).to_public_dict()


@router.get("/v1/knowledge/market")
def get_market_bundle(request: Request, question: str | None = None) -> dict:
    gateway = _app_state(request).gateway
    return gateway.retrieve(query_type="market", question=question).to_public_dict()


@router.post("/v1/knowledge/compare")
def post_compare(request: Request, body: CompareRequest | None = None) -> dict:
    payload = body or CompareRequest()
    if len(payload.symbols) < 2:
        raise HTTPException(status_code=400, detail="compare_requires_two_symbols")
    gateway = _app_state(request).gateway
    return gateway.compare_bundle(payload.symbols, question=payload.question).to_public_dict()


@router.get("/v1/internal/krig/metrics")
def krig_metrics(request: Request) -> dict:
    return {"metrics": _app_state(request).store.retrieval_metrics_snapshot()}


@router.get("/v1/internal/jobs")
def list_jobs(request: Request) -> dict:
    scheduler = _app_state(request).scheduler
    return {"jobs": scheduler.list_jobs() if scheduler else []}


@router.get("/v1/internal/metrics")
def metrics(request: Request) -> dict:
    from app.metrics.metrics import METRICS

    return METRICS.snapshot()


# ----- Sprint 6.5 AKO (Mission Control soft surface) -----

class AkoEventRequest(BaseModel):
    kind: str
    title: str
    event_date: str  # YYYY-MM-DD
    symbols: list[str] = Field(default_factory=list)
    boost_multiplier: float = 2.0
    priority: int = 80


def _require_ako(request: Request):
    ako = getattr(_app_state(request), "ako", None)
    if ako is None:
        raise HTTPException(status_code=503, detail="ako_disabled")
    return ako


@router.get("/v1/ako/mission-control")
def ako_mission_control(request: Request) -> dict:
    """Mission Control: collector health, intervals, queue, freshness, events."""
    return _require_ako(request).mission_control_snapshot()


@router.get("/v1/ako/session")
def ako_session(request: Request) -> dict:
    from app.ako.sessions import next_session_boundary, resolve_session

    session = resolve_session()
    return {
        "current": session.session.value,
        "label": session.label,
        "as_of_ist": session.as_of_ist.isoformat(),
        "is_trading_day": session.is_trading_day,
        "allow_live_polling": session.allow_live_polling,
        "allow_heavy_rebuild": session.allow_heavy_rebuild,
        "next_boundary_ist": next_session_boundary(session.as_of_ist).isoformat(),
    }


@router.get("/v1/ako/events")
def ako_events(request: Request) -> dict:
    return _require_ako(request).event_engine.snapshot()


@router.post("/v1/ako/events")
def ako_register_event(request: Request, body: AkoEventRequest) -> dict:
    from datetime import date as date_cls

    try:
        event_date = date_cls.fromisoformat(body.event_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid_event_date") from exc
    return _require_ako(request).register_event(
        kind=body.kind,
        title=body.title,
        event_date=event_date,
        symbols=body.symbols,
        boost_multiplier=body.boost_multiplier,
        priority=body.priority,
    )


@router.get("/v1/ako/jobs")
def ako_jobs(request: Request) -> dict:
    snap = _require_ako(request).mission_control_snapshot()
    return {
        "session": snap["session"],
        "jobs": snap["jobs"],
        "queue_depth": snap["queue_depth"],
        "dead_letter_count": snap["dead_letter_count"],
    }


@router.get("/v1/ako/telemetry")
def ako_telemetry(request: Request) -> dict:
    return _require_ako(request).telemetry.snapshot()


@router.get("/v1/ako/freshness")
def ako_freshness(request: Request) -> dict:
    """Mission Control — Knowledge Freshness Engine portfolio view."""
    snap = _require_ako(request).mission_control_snapshot()
    return {"freshness": snap.get("freshness"), "session": snap.get("session")}


@router.get("/v1/ako/confidence")
def ako_confidence(request: Request) -> dict:
    """Mission Control — Knowledge Confidence Engine portfolio view."""
    snap = _require_ako(request).mission_control_snapshot()
    return {"confidence": snap.get("confidence"), "session": snap.get("session")}


@router.get("/v1/knowledge/freshness/{object_type}/{subject_key}")
def get_object_freshness(object_type: str, subject_key: str, request: Request) -> dict:
    """Per-object freshness: age, status, current-as-of statement."""
    from app.kfe.engine import KnowledgeFreshnessEngine

    store = _app_state(request).store
    engine = KnowledgeFreshnessEngine()
    row = store.get_freshness(object_type=object_type, subject_key=subject_key)
    report = engine.object_report(
        object_type,
        updated_at=(row or {}).get("updated_at"),
        present=row is not None,
        subject=subject_key,
    )
    return {"object_type": object_type, "subject_key": subject_key, "freshness": report, "registry": row}


@router.get("/v1/knowledge/confidence/{object_type}/{subject_key}")
def get_object_confidence(object_type: str, subject_key: str, request: Request) -> dict:
    """Per-object confidence: trust score from multi-source agreement."""
    store = _app_state(request).store
    row = store.get_confidence(object_type=object_type, subject_key=subject_key)
    if not row:
        raise HTTPException(status_code=404, detail="confidence_not_found")
    return {"object_type": object_type, "subject_key": subject_key, "confidence": row}


@router.post("/v1/ako/tick")
def ako_tick(request: Request) -> dict:
    """Ops-only: force one AKO evaluation cycle (does not serve Ask)."""
    executed = _require_ako(request).tick_once()
    return {"executed": executed, "count": len(executed)}


@router.post("/v1/internal/run/{collector_id}")
def run_collector(collector_id: str, request: Request) -> dict:
    """Ops-only: run one registered collector immediately.

    Hard boundary: this endpoint is for Mission Control / ops — never called
    by Ask or the Intelligence Engine judgment path.
    """
    state = _app_state(request)
    collectors = state.collectors
    collector = collectors.get(collector_id)
    if not collector:
        raise HTTPException(status_code=404, detail="collector_not_found")
    result = state.pipeline.run_collector(collector)
    from app.metrics.metrics import METRICS

    METRICS.record_run(
        collector_id,
        accepted=len(result.accepted),
        rejected=len(result.rejected),
        duplicates=len(result.duplicates),
        published=len(result.knowledge_objects),
        learning=len(result.learning_events),
    )
    return {
        "collector_id": collector_id,
        "accepted": len(result.accepted),
        "rejected": len(result.rejected),
        "duplicates": len(result.duplicates),
        "published_objects": len(result.knowledge_objects),
        "learning_events": len(result.learning_events),
        "envelope": result.published.envelope.model_dump(mode="json") if result.published and result.published.envelope else None,
    }
