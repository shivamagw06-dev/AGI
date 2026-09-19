"""IMEI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from knowledge_factory.market_expectations_intelligence import store as imei_store
from knowledge_factory.market_expectations_intelligence.collectors.consensus_licensed import (
    collect_licensed_consensus,
    licensed_consensus_available,
)
from knowledge_factory.market_expectations_intelligence.dashboards import expectations_dashboard
from knowledge_factory.market_expectations_intelligence.expectations.views import (
    company_expectations,
    expectation_gap,
)
from knowledge_factory.market_expectations_intelligence.narratives.registry import narrative_view
from knowledge_factory.market_expectations_intelligence.pipeline import (
    run_market_expectations_pipeline,
)
from knowledge_factory.market_expectations_intelligence.registry.catalog import registry_snapshot
from knowledge_factory.market_expectations_intelligence.schema import (
    FREEZE_LOCKS,
    IMEI_VERSION,
    LAYER,
    PROGRAMME,
)


def _ensure() -> None:
    if imei_store.expectation_count() == 0:
        run_market_expectations_pipeline()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": IMEI_VERSION,
        "architecture_status": "SOFT_MARKET_EXPECTATIONS_INTELLIGENCE",
        "delivery_phase": "phase_1_public_auditable",
        "principle": "Markets price expectations, not reality.",
        "not_a_reasoning_engine": True,
        "not_a_prediction_engine": True,
        "not_broker_report_ingestion": True,
        "not_recommendation_aggregation": True,
        "not_sentiment_analysis": True,
        "never_fabricate": True,
        "point_in_time_integrity": True,
        "soft_wire_only": True,
        "phase_2_licensed_consensus_available": licensed_consensus_available(),
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/expectations",
        "modules": [
            "Expectation Objects",
            "Consensus Proxy (Phase-1)",
            "Revision Intelligence",
            "Surprise Intelligence",
            "Expectation Gap",
            "Narrative Registry",
            "Historical Replay",
            "Morning Board",
            "Phase-2 Licensed Consensus Collector (modular)",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return expectations_dashboard(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_market_expectations_pipeline()


def registry() -> dict[str, Any]:
    return registry_snapshot()


def company(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    return company_expectations(ticker, as_of=as_of)


def gap(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    return expectation_gap(ticker, as_of=as_of)


def revisions(*, entity: str | None = None, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    rows = imei_store.list_revisions(entity=entity, as_of=as_of)
    return {
        "n": len(rows),
        "revisions": rows,
        "entity": entity,
        "as_of": as_of,
        "version": IMEI_VERSION,
        "fabricated": False,
    }


def surprises(*, entity: str | None = None, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    rows = imei_store.list_surprises(entity=entity, as_of=as_of)
    return {
        "n": len(rows),
        "surprises": rows,
        "entity": entity,
        "as_of": as_of,
        "version": IMEI_VERSION,
        "fabricated": False,
        "prediction": False,
    }


def narratives(narrative_id: str | None = None) -> dict[str, Any]:
    _ensure()
    return narrative_view(narrative_id)


def search(q: str = "", *, limit: int = 25) -> dict[str, Any]:
    _ensure()
    query = str(q or "").strip().lower()
    hits = []
    for e in imei_store.list_expectations():
        blob = " ".join(
            [
                str(e.get("entity") or ""),
                str(e.get("metric") or ""),
                str(e.get("period") or ""),
                str(e.get("kind") or ""),
                str(e.get("source") or ""),
            ]
        ).lower()
        if not query or query in blob:
            hits.append(
                {
                    "expectation_id": e.get("expectation_id"),
                    "entity": e.get("entity"),
                    "metric": e.get("metric"),
                    "period": e.get("period"),
                    "kind": e.get("kind"),
                    "forecast_value": e.get("forecast_value"),
                    "available_from": e.get("available_from"),
                    "source": e.get("source"),
                    "confidence": e.get("confidence"),
                }
            )
        if len(hits) >= limit:
            break
    return {"q": q, "n": len(hits), "results": hits, "version": IMEI_VERSION}


def replay(*, as_of: str, entity: str | None = None) -> dict[str, Any]:
    _ensure()
    exps = imei_store.list_expectations(entity=entity, as_of=as_of)
    revs = imei_store.list_revisions(entity=entity, as_of=as_of)
    surps = imei_store.list_surprises(entity=entity, as_of=as_of)
    leaked = [e for e in exps if str(e.get("available_from") or "") > as_of]
    return {
        "as_of": as_of,
        "entity": entity,
        "n_expectations": len(exps),
        "n_revisions": len(revs),
        "n_surprises": len(surps),
        "expectations": [
            {
                "expectation_id": e.get("expectation_id"),
                "entity": e.get("entity"),
                "metric": e.get("metric"),
                "period": e.get("period"),
                "kind": e.get("kind"),
                "forecast_value": e.get("forecast_value"),
                "available_from": e.get("available_from"),
            }
            for e in exps
        ],
        "future_leak": len(leaked) > 0,
        "version": IMEI_VERSION,
        "fabricated": False,
    }


def phase2_consensus_status() -> dict[str, Any]:
    return collect_licensed_consensus()
