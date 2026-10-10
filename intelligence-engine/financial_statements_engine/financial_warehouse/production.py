"""FSE-06 Mission Control façades for the Financial Warehouse."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.financial_warehouse.contracts.layer import fetch_contract, list_contracts
from financial_statements_engine.financial_warehouse.observability.metrics import warehouse_metrics
from financial_statements_engine.financial_warehouse.publisher.publish import publish_validated_pack
from financial_statements_engine.financial_warehouse.query.api import (
    company_timeline,
    latest_financials,
    metric_history,
    version_history,
)
from financial_statements_engine.financial_warehouse.restatements.engine import record_restatement, restatement_history
from financial_statements_engine.financial_warehouse.schema import (
    CONTRACT_IDS,
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    QUALITY_GUARANTEES,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VERSION,
    VIEWS,
    WAREHOUSE_VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.financial_warehouse.time_travel.views import query_view
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "warehouse_version": WAREHOUSE_VERSION,
        "capabilities": [
            "validated_facts_only",
            "write_once_versioning",
            "restatements",
            "time_travel",
            "lineage",
            "indexing",
            "query",
            "data_contracts",
            "mission_control",
        ],
        "quality_guarantees": list(QUALITY_GUARANTEES),
        "views": list(VIEWS),
        "contracts": list(CONTRACT_IDS),
        "never_validates_accounting": True,
        "never_stores_drafts": True,
        "never_stores_raw_evidence": True,
        "consumers_must_use_contracts": True,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_06_FINANCIAL_WAREHOUSE.md",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    m = warehouse_metrics()
    events = [e for e in get_bus().tail(300) if "warehouse." in str(e.get("event_type"))]
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "warehouse_health": "ok",
        "storage_dashboard": m,
        "restatement_n": m["restatement_n"],
        "recent_warehouse_events": events[-30:],
        "contracts": list(CONTRACT_IDS),
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def publish(validated_pack: dict[str, Any], draft: dict[str, Any] | None = None) -> dict[str, Any]:
    return publish_validated_pack(validated_pack=validated_pack, draft=draft)


def get_latest(ticker: str, statement_type: str | None = None) -> dict[str, Any]:
    return latest_financials(ticker, statement_type=statement_type)


def get_metric_history(ticker: str, metric: str) -> dict[str, Any]:
    return metric_history(ticker, metric)


def get_timeline(ticker: str) -> dict[str, Any]:
    return company_timeline(ticker)


def get_versions(company_id: str, fact_key: str) -> dict[str, Any]:
    return version_history(company_id, fact_key)


def time_travel(ticker: str, view: str, as_of: str | None = None) -> dict[str, Any]:
    return query_view(ticker, view, as_of=as_of)


def restatements(company_id: str | None = None) -> dict[str, Any]:
    rows = restatement_history(company_id)
    return {"ok": True, "n": len(rows), "restatements": rows}


def restate(
    validated_pack: dict[str, Any],
    *,
    reason: str,
    draft: dict[str, Any] | None = None,
    original_validation_id: str | None = None,
) -> dict[str, Any]:
    return record_restatement(
        validated_pack=validated_pack,
        draft=draft,
        restatement_reason=reason,
        original_validation_id=original_validation_id,
    )


def contracts() -> dict[str, Any]:
    return list_contracts()


def contract(contract_id: str, ticker: str, **kwargs: Any) -> dict[str, Any]:
    return fetch_contract(contract_id, ticker, **kwargs)
