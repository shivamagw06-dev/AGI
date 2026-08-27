"""Derived metric data contracts — consumers never read the DME store directly."""

from __future__ import annotations

from typing import Any, Callable

from financial_statements_engine.derived_metrics.schema import CONTRACT_METRIC_SETS, DME_VERSION, METRIC_CONTRACTS
from financial_statements_engine.derived_metrics.store.versions import list_company_metrics, load_latest
from financial_statements_engine.financial_warehouse.production import get_latest
from financial_statements_engine.util import now_iso


def _company_period(ticker: str) -> tuple[str, str]:
    t = ticker.upper().strip()
    pack = get_latest(t)
    company_id = next(
        (f.get("company_id") for f in (pack.get("facts") or []) if f.get("company_id")),
        f"nse:{t}",
    )
    period = next(
        (f.get("reporting_period") for f in (pack.get("facts") or []) if f.get("reporting_period")),
        None,
    )
    if period is None:
        # Fall back to latest period present in the DME store index
        rows = list_company_metrics(str(company_id))
        if rows:
            # Prefer highest metric_version row's period
            best = max(rows, key=lambda r: int(r.get("metric_version") or 0))
            period = best.get("period")
    return str(company_id), str(period or "unknown")


def _load_set(ticker: str, names: tuple[str, ...]) -> dict[str, Any]:
    t = ticker.upper().strip()
    company_id, period = _company_period(t)
    wanted = set(names) if names else None
    metrics: dict[str, Any] = {}
    # Prefer latest pointers for requested names; fall back to index for api_metrics.v1 (all)
    if wanted is None:
        rows = list_company_metrics(company_id)
        # keep highest version per metric_name for this period
        best: dict[str, dict[str, Any]] = {}
        for r in rows:
            if r.get("period") != period:
                continue
            name = str(r["metric_name"])
            prev = best.get(name)
            if prev is None or int(r.get("metric_version") or 0) > int(prev.get("metric_version") or 0):
                best[name] = r
        for name in best:
            full = load_latest(company_id, period, name)
            if full and full.get("quality_status") == "calculated":
                metrics[name] = {
                    "metric_id": full.get("metric_id"),
                    "value": full.get("value"),
                    "formula_version": full.get("formula_version"),
                    "quality_status": full.get("quality_status"),
                    "lineage_reference": full.get("lineage_reference"),
                    "metric_version": full.get("metric_version"),
                }
    else:
        for name in sorted(wanted):
            full = load_latest(company_id, period, name)
            if full and full.get("quality_status") == "calculated":
                metrics[name] = {
                    "metric_id": full.get("metric_id"),
                    "value": full.get("value"),
                    "formula_version": full.get("formula_version"),
                    "quality_status": full.get("quality_status"),
                    "lineage_reference": full.get("lineage_reference"),
                    "metric_version": full.get("metric_version"),
                }
    return {
        "ticker": t,
        "company_id": company_id,
        "period": period,
        "metrics": metrics,
        "n": len(metrics),
    }


def _contract_factory(contract_id: str) -> Callable[..., dict[str, Any]]:
    names = CONTRACT_METRIC_SETS.get(contract_id, ())

    def _fn(ticker: str, **kwargs: Any) -> dict[str, Any]:
        payload = _load_set(ticker, names)
        return {
            "contract_id": contract_id,
            **payload,
            "publication_timestamp": now_iso(),
        }

    return _fn


CONTRACT_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    cid: _contract_factory(cid) for cid in METRIC_CONTRACTS
}


def list_contracts() -> dict[str, Any]:
    return {
        "ok": True,
        "dme_version": DME_VERSION,
        "contracts": list(METRIC_CONTRACTS),
        "rule": "consumers_must_use_metric_contracts_not_direct_storage",
        "as_of": now_iso(),
    }


def fetch_contract(contract_id: str, ticker: str, **kwargs: Any) -> dict[str, Any]:
    fn = CONTRACT_REGISTRY.get(contract_id)
    if fn is None:
        return {
            "ok": False,
            "error": "unknown_contract",
            "contract_id": contract_id,
            "supported": list(METRIC_CONTRACTS),
        }
    payload = fn(ticker, **kwargs)
    return {
        "ok": True,
        "contract_id": contract_id,
        "dme_version": DME_VERSION,
        "direct_storage_access": False,
        "data": payload,
        "as_of": now_iso(),
        "issues_recommendations": False,
    }
