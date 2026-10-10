"""Publish Validated Financial Facts into the warehouse (write-once)."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.financial_warehouse.indexing.engine import index_fact
from financial_statements_engine.financial_warehouse.lineage.links import build_lineage_refs
from financial_statements_engine.financial_warehouse.schema import PUBLISHABLE_STATUSES, WAREHOUSE_VERSION
from financial_statements_engine.financial_warehouse.storage.roots import store_fact_record
from financial_statements_engine.financial_warehouse.versioning.engine import (
    list_fact_versions,
    next_version,
    register_version,
    supersede,
)
from financial_statements_engine.util import now_iso


def _fact_key(company_id: str, statement_type: str, metric: str, period: str) -> str:
    raw = f"{company_id}|{statement_type}|{metric}|{period}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _company_id(draft_or_pack: dict[str, Any]) -> str:
    if draft_or_pack.get("company_id"):
        return str(draft_or_pack["company_id"])
    ticker = str(draft_or_pack.get("ticker") or "UNKNOWN").upper()
    return f"nse:{ticker}"


def publish_validated_pack(
    *,
    validated_pack: dict[str, Any],
    draft: dict[str, Any] | None = None,
    reason_for_change: str | None = None,
    is_restatement: bool = False,
    restatement_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest a VFQE-validated pack. Rejects non-publishable approval statuses."""
    status = str(
        validated_pack.get("approval_status")
        or validated_pack.get("validation_status")
        or ""
    )
    if status not in PUBLISHABLE_STATUSES:
        publish(
            "warehouse.publish_rejected.v1",
            {"reason": "not_publishable", "approval_status": status},
        )
        return {
            "ok": False,
            "published": False,
            "reason": "not_publishable",
            "approval_status": status,
        }

    facts_in = list(validated_pack.get("facts") or [])
    if not facts_in:
        return {"ok": False, "published": False, "reason": "no_facts"}

    company_id = _company_id(draft or validated_pack)
    ticker = str((draft or validated_pack).get("ticker") or company_id.split(":")[-1]).upper()
    period = (
        ((draft or {}).get("period") or {}).get("period_end")
        or validated_pack.get("period_end")
        or "unknown"
    )
    period_kind = ((draft or {}).get("period") or {}).get("period_kind")
    fiscal_year = None
    if isinstance(period, str) and len(period) >= 4:
        fiscal_year = period[:4]
    currency = ((draft or {}).get("currency") or {}).get("canonical_currency") or "INR"
    published_at = now_iso()
    lineage = build_lineage_refs(draft or {}, validated_pack)

    stored: list[dict[str, Any]] = []
    for raw in facts_in:
        metric = str(raw.get("metric") or raw.get("canonical_metric") or "")
        if not metric:
            continue
        statement_type = str(raw.get("statement_type") or "unknown")
        fkey = _fact_key(company_id, statement_type, metric, str(period))
        version = next_version(company_id, fkey)
        fact_id = f"fact:{uuid.uuid4().hex[:16]}"

        # Supersede prior latest if exists
        prior = list_fact_versions(company_id, fkey)
        if prior:
            last = prior[-1]
            supersede(
                company_id,
                fkey,
                int(last["version_number"]),
                superseded_by_fact_id=fact_id,
                superseded_date=published_at,
            )

        record = {
            "fact_id": fact_id,
            "fact_key": fkey,
            "company_id": company_id,
            "ticker": ticker,
            "statement_type": statement_type,
            "metric": metric,
            "canonical_metric": metric,
            "value": raw.get("value") if raw.get("value") is not None else raw.get("normalized_value"),
            "reported_value": raw.get("reported_value"),
            "normalized_value": raw.get("normalized_value"),
            "currency": currency,
            "unit": raw.get("unit") or raw.get("scale") or "crores",
            "reporting_period": period,
            "fiscal_year": fiscal_year,
            "quarter": ((draft or {}).get("period") or {}).get("quarter"),
            "statement_date": period,
            "validation_id": validated_pack.get("validation_id") or raw.get("validation_id"),
            "quality_score": validated_pack.get("quality_score") or raw.get("quality_score"),
            "validation_status": status,
            "version": version,
            "published_timestamp": published_at,
            "effective_date": period,
            "superseded_by": None,
            "lineage_reference": lineage,
            "manifest_reference": lineage.get("manifest_id"),
            "coverage_reference": lineage.get("coverage_matrix_id"),
            "source_reference": lineage.get("document_hash"),
            "source_draft_id": lineage.get("draft_id"),
            "warehouse_version": WAREHOUSE_VERSION,
            "immutable": True,
            "is_restatement": is_restatement,
            "restatement": restatement_meta,
            "reason_for_change": reason_for_change or ("restatement" if is_restatement else "initial_publish"),
            "validator_version": raw.get("validator_version"),
            "schema_version": (draft or {}).get("manifest", {}).get("schema_version")
            if draft
            else None,
            "issues_recommendations": False,
        }
        path = store_fact_record(record)
        register_version(
            company_id=company_id,
            fact_key=fkey,
            fact_id=fact_id,
            version_number=version,
            published_timestamp=published_at,
            effective_date=period,
            reason_for_change=record["reason_for_change"],
            validator_version=record.get("validator_version"),
            schema_version=record.get("schema_version"),
            path=str(path),
        )
        index_fact(record)
        stored.append(record)

    publish(
        "warehouse.facts_published.v1",
        {
            "company_id": company_id,
            "ticker": ticker,
            "fact_n": len(stored),
            "validation_id": validated_pack.get("validation_id"),
            "approval_status": status,
        },
    )
    return {
        "ok": True,
        "published": True,
        "company_id": company_id,
        "ticker": ticker,
        "fact_n": len(stored),
        "facts": stored,
        "warehouse_version": WAREHOUSE_VERSION,
        "issues_recommendations": False,
    }
