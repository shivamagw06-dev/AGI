"""Persist calculation results as immutable derived metric versions + publish event."""

from __future__ import annotations

import uuid
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.derived_metrics.schema import DME_VERSION, DerivedMetricRecord
from financial_statements_engine.derived_metrics.store.versions import (
    next_metric_version,
    store_failure_report,
    store_metric,
)
from financial_statements_engine.financial_warehouse.schema import WAREHOUSE_VERSION
from financial_statements_engine.util import now_iso


def persist_calculation(result: dict[str, Any]) -> dict[str, Any]:
    """Store successful metrics; record failure reports. Never overwrites history."""
    company_id = str(result.get("company_id") or f"nse:{result.get('ticker', 'UNKNOWN')}")
    ticker = str(result.get("ticker") or company_id.split(":")[-1]).upper()
    period = str(result.get("period") or "unknown")
    ts = str(result.get("as_of") or now_iso())
    stored: list[dict[str, Any]] = []
    failures_stored: list[str] = []

    for name, row in (result.get("metrics") or {}).items():
        version = next_metric_version(company_id, period, name)
        metric_id = f"dmet:{uuid.uuid4().hex[:16]}"
        record = DerivedMetricRecord(
            metric_id=metric_id,
            company_id=company_id,
            ticker=ticker,
            period=period,
            metric_name=name,
            value=float(row["value"]),
            formula_id=str(row["formula_id"]),
            formula_version=str(row["formula_version"]),
            metric_version=version,
            calculation_version=str(row.get("fingerprint") or DME_VERSION),
            quality_status=str(row.get("quality_status") or "calculated"),
            source_fact_ids=list(row.get("source_fact_ids") or []),
            lineage_path=list(row.get("lineage_path") or []),
            lineage_reference=f"lineage:{metric_id}",
            warehouse_version=WAREHOUSE_VERSION,
            fingerprint=row.get("fingerprint"),
            category=row.get("category"),
            effective_date=period,
            published_timestamp=ts,
            calculation_timestamp=str(row.get("calculation_timestamp") or ts),
            dme_version=DME_VERSION,
        )
        path = store_metric(record)
        stored.append({"metric_name": name, "metric_id": metric_id, "metric_version": version, "path": str(path)})

    for fail in result.get("failures") or []:
        path = store_failure_report(
            {
                **fail,
                "company_id": company_id,
                "ticker": ticker,
                "period": period,
                "metric_name": fail.get("metric"),
                "calculation_timestamp": ts,
                "dme_version": DME_VERSION,
            }
        )
        failures_stored.append(str(path))

    if stored:
        publish(
            "derived_metrics.calculated.v1",
            {
                "ticker": ticker,
                "company_id": company_id,
                "period": period,
                "n": len(stored),
                "failures_n": len(failures_stored),
            },
        )
        publish(
            "derived_metrics.published.v1",
            {"ticker": ticker, "company_id": company_id, "period": period, "n": len(stored)},
        )
    if failures_stored:
        publish(
            "derived_metrics.calculation_failed.v1",
            {"ticker": ticker, "company_id": company_id, "period": period, "n": len(failures_stored)},
        )

    return {
        "ok": True,
        "ticker": ticker,
        "company_id": company_id,
        "period": period,
        "stored_n": len(stored),
        "stored": stored,
        "failures_stored_n": len(failures_stored),
        "mutates_warehouse_facts": False,
        "as_of": ts,
    }
