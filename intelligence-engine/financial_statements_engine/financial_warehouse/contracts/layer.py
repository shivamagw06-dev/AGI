"""Consumers read contracts, never warehouse files/tables directly."""

from __future__ import annotations

from typing import Any, Callable

from financial_statements_engine.financial_warehouse.query.api import latest_financials, metric_history
from financial_statements_engine.financial_warehouse.schema import CONTRACT_IDS, WAREHOUSE_VERSION
from financial_statements_engine.financial_warehouse.time_travel.views import query_view
from financial_statements_engine.util import now_iso


def _shape_facts(facts: list[dict[str, Any]], *, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    out = []
    for f in facts:
        out.append({k: f.get(k) for k in fields})
    return out


def _dcf_v1(ticker: str, **kwargs: Any) -> dict[str, Any]:
    raw = latest_financials(ticker)
    fields = (
        "metric",
        "value",
        "currency",
        "unit",
        "reporting_period",
        "statement_type",
        "quality_score",
        "validation_id",
        "version",
    )
    return {
        "contract_id": "dcf.v1",
        "ticker": ticker.upper().strip(),
        "facts": _shape_facts(raw.get("facts") or [], fields=fields),
        "n": raw.get("n"),
    }


def _forecast_v1(ticker: str, **kwargs: Any) -> dict[str, Any]:
    raw = latest_financials(ticker)
    fields = ("metric", "value", "reporting_period", "fiscal_year", "statement_type", "version")
    return {
        "contract_id": "forecast.v1",
        "ticker": ticker.upper().strip(),
        "series": _shape_facts(raw.get("facts") or [], fields=fields),
    }


def _screener_v1(ticker: str, **kwargs: Any) -> dict[str, Any]:
    raw = latest_financials(ticker)
    # Flat metric map for screening
    metrics = {
        str(f.get("metric")): f.get("value")
        for f in (raw.get("facts") or [])
        if f.get("metric") is not None
    }
    return {
        "contract_id": "screener.v1",
        "ticker": ticker.upper().strip(),
        "metrics": metrics,
        "quality_ok": all(
            (f.get("validation_status") in ("APPROVED", "APPROVED_WITH_WARNINGS"))
            for f in (raw.get("facts") or [])
        )
        if raw.get("facts")
        else False,
    }


def _api_v1(ticker: str, **kwargs: Any) -> dict[str, Any]:
    view = str(kwargs.get("view") or "latest")
    as_of = kwargs.get("as_of")
    raw = query_view(ticker, view, as_of=as_of)
    return {
        "contract_id": "api.v1",
        "ticker": ticker.upper().strip(),
        "view": view,
        "payload": raw,
    }


def _ask_agib_v1(ticker: str, **kwargs: Any) -> dict[str, Any]:
    raw = latest_financials(ticker)
    metric = kwargs.get("metric")
    hist = metric_history(ticker, str(metric)) if metric else None
    return {
        "contract_id": "ask_agib.v1",
        "ticker": ticker.upper().strip(),
        "snapshot": [
            {
                "metric": f.get("metric"),
                "value": f.get("value"),
                "period": f.get("reporting_period"),
                "trace": {
                    "validation_id": f.get("validation_id"),
                    "manifest_reference": f.get("manifest_reference"),
                    "coverage_reference": f.get("coverage_reference"),
                    "lineage_reference": f.get("lineage_reference"),
                },
            }
            for f in (raw.get("facts") or [])
        ],
        "metric_history": hist,
    }


CONTRACT_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "dcf.v1": _dcf_v1,
    "forecast.v1": _forecast_v1,
    "screener.v1": _screener_v1,
    "api.v1": _api_v1,
    "ask_agib.v1": _ask_agib_v1,
}


def list_contracts() -> dict[str, Any]:
    return {
        "ok": True,
        "warehouse_version": WAREHOUSE_VERSION,
        "contracts": list(CONTRACT_IDS),
        "rule": "consumers_must_use_contracts_not_direct_storage",
        "as_of": now_iso(),
    }


def fetch_contract(contract_id: str, ticker: str, **kwargs: Any) -> dict[str, Any]:
    fn = CONTRACT_REGISTRY.get(contract_id)
    if fn is None:
        return {
            "ok": False,
            "error": "unknown_contract",
            "contract_id": contract_id,
            "supported": list(CONTRACT_IDS),
        }
    payload = fn(ticker, **kwargs)
    return {
        "ok": True,
        "contract_id": contract_id,
        "warehouse_version": WAREHOUSE_VERSION,
        "direct_storage_access": False,
        "data": payload,
        "as_of": now_iso(),
        "issues_recommendations": False,
    }
