"""FSE-07 Mission Control façades for the Derived Metrics Engine."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.collection.event_bus import get_bus
from financial_statements_engine.derived_metrics.calculation.engine import calculate_company
from financial_statements_engine.derived_metrics.dependency.graph import dependency_lineage, impacted_metrics
from financial_statements_engine.derived_metrics.formula_registry.registry import list_formulas, resolve_order
from financial_statements_engine.derived_metrics.observability.metrics import dme_metrics
from financial_statements_engine.derived_metrics.publication.contracts import fetch_contract, list_contracts
from financial_statements_engine.derived_metrics.publication.persist import persist_calculation
from financial_statements_engine.derived_metrics.restatement.recalc import recalculate_for_changed_facts
from financial_statements_engine.derived_metrics.schema import (
    DME_VERSION,
    ISSUES_RECOMMENDATIONS,
    METRIC_CONTRACTS,
    PROGRAMME,
    QUALITY_TARGETS,
    RECOMMENDATION_POLICY,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.derived_metrics.store.versions import list_company_metrics, load_latest
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "dme_version": DME_VERSION,
        "capabilities": [
            "formula_registry",
            "dependency_resolver",
            "deterministic_calculation",
            "immutable_metric_store",
            "lineage",
            "restatement_recalculation",
            "metric_data_contracts",
            "mission_control",
        ],
        "quality_targets": dict(QUALITY_TARGETS),
        "contracts": list(METRIC_CONTRACTS),
        "formulas_n": len(list_formulas()),
        "consumes_only_warehouse_facts": True,
        "never_mutates_warehouse_facts": True,
        "never_consumes_drafts_or_raw": True,
        "consumers_must_use_contracts": True,
        "no_independent_consumer_formulas": True,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": "docs/FSE_07_DERIVED_METRICS_ENGINE.md",
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    m = dme_metrics()
    events = [e for e in get_bus().tail(300) if "derived_metrics." in str(e.get("event_type"))]
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "dme_health": "ok",
        "calculation_queue": "idle",
        "metric_coverage": m,
        "formula_usage": m.get("formulas_by_category"),
        "failed_calculations": m.get("calculation_failures"),
        "recent_dme_events": events[-30:],
        "contracts": list(METRIC_CONTRACTS),
        "issues_recommendations": False,
        "as_of": now_iso(),
    }


def calculate(
    ticker: str,
    *,
    metrics: list[str] | None = None,
    persist: bool = True,
    facts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    calc = calculate_company(ticker, metrics=metrics, facts=facts)
    out: dict[str, Any] = {"ok": True, "calculation": calc}
    if persist:
        out["persisted"] = persist_calculation(calc)
    return out


def formulas(*, category: str | None = None) -> dict[str, Any]:
    rows = list_formulas(category=category)
    return {
        "ok": True,
        "n": len(rows),
        "formulas": rows,
        "resolve_order": resolve_order([r["metric_name"] for r in rows]),
        "as_of": now_iso(),
    }


def lineage(metric_name: str) -> dict[str, Any]:
    return dependency_lineage(metric_name)


def impact(changed_fact_metrics: list[str]) -> dict[str, Any]:
    return {"ok": True, "changed": list(changed_fact_metrics), "impacted": impacted_metrics(changed_fact_metrics)}


def recalculate(ticker: str, changed_fact_metrics: list[str]) -> dict[str, Any]:
    return recalculate_for_changed_facts(ticker, changed_fact_metrics)


def contracts() -> dict[str, Any]:
    return list_contracts()


def contract(contract_id: str, ticker: str, **kwargs: Any) -> dict[str, Any]:
    return fetch_contract(contract_id, ticker, **kwargs)


def company_metrics(ticker: str) -> dict[str, Any]:
    t = ticker.upper().strip()
    company_id = f"nse:{t}"
    rows = list_company_metrics(company_id)
    # also try whatever company_id warehouse used
    if not rows:
        from financial_statements_engine.financial_warehouse.production import get_latest

        pack = get_latest(t)
        cid = next((f.get("company_id") for f in (pack.get("facts") or []) if f.get("company_id")), None)
        if cid:
            company_id = str(cid)
            rows = list_company_metrics(company_id)
    return {"ok": True, "ticker": t, "company_id": company_id, "n": len(rows), "metrics": rows}


def get_metric(ticker: str, metric_name: str, period: str | None = None) -> dict[str, Any]:
    from financial_statements_engine.financial_warehouse.production import get_latest

    t = ticker.upper().strip()
    pack = get_latest(t)
    company_id = next(
        (f.get("company_id") for f in (pack.get("facts") or []) if f.get("company_id")),
        f"nse:{t}",
    )
    per = period or next(
        (f.get("reporting_period") for f in (pack.get("facts") or []) if f.get("reporting_period")),
        "unknown",
    )
    row = load_latest(str(company_id), str(per), metric_name)
    return {
        "ok": row is not None,
        "ticker": t,
        "company_id": company_id,
        "period": per,
        "metric_name": metric_name,
        "metric": row,
    }
