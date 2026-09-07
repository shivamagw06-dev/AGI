"""Publish Validated Financial Facts to the Financial Warehouse."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.store import ensure_dirs, paths_for
from financial_statements_engine.util import now_iso, write_json_atomic
from financial_statements_engine.validation.findings import extract_metrics
from financial_statements_engine.validation.schema import VALIDATOR_VERSION


def build_validated_facts(draft: dict[str, Any], report: dict[str, Any]) -> list[dict[str, Any]]:
    """Create immutable validated fact records from an approved draft. Never edits draft values."""
    metrics = extract_metrics(draft)
    facts: list[dict[str, Any]] = []
    published_at = now_iso()
    for metric, row in sorted(metrics.items()):
        facts.append(
            {
                "metric": metric,
                "value": row.get("value") if isinstance(row, dict) else row,
                "reported_value": row.get("reported_value") if isinstance(row, dict) else None,
                "normalized_value": row.get("normalized_value") if isinstance(row, dict) else None,
                "statement_type": row.get("statement_type") if isinstance(row, dict) else None,
                "validation_id": report["validation_id"],
                "quality_score": (report.get("quality_score") or {}).get("score"),
                "quality_grade": (report.get("quality_score") or {}).get("grade"),
                "validation_status": (report.get("approval") or {}).get("approval_status"),
                "validator_version": VALIDATOR_VERSION,
                "published_timestamp": published_at,
                "source_draft_id": draft.get("draft_id"),
                "manifest_id": draft.get("manifest_id"),
                "coverage_matrix_id": draft.get("coverage_matrix_id"),
                "document_hash": draft.get("document_hash"),
                "ticker": draft.get("ticker"),
                "immutable": True,
            }
        )
    return facts


def publish_validated_facts(draft: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Write validated facts only when approval is publishable. Draft is never mutated."""
    approval = report.get("approval") or {}
    if not approval.get("publishable"):
        return {
            "ok": False,
            "published": False,
            "reason": "not_publishable",
            "approval_status": approval.get("approval_status"),
        }

    ticker = str(draft.get("ticker") or "").upper().strip()
    facts = build_validated_facts(draft, report)
    pub = paths_for(ticker)["published"]
    pub.mkdir(parents=True, exist_ok=True)
    pack_path = pub / f"validated_{report['validation_id'].replace(':', '_')}.json"
    if pack_path.exists():
        raise FileExistsError(f"validated_facts_immutable_violation: {report['validation_id']}")

    pack = {
        "ticker": ticker,
        "validation_id": report["validation_id"],
        "draft_id": draft.get("draft_id"),
        "approval_status": approval.get("approval_status"),
        "quality_score": report.get("quality_score"),
        "validator_version": VALIDATOR_VERSION,
        "published_at": now_iso(),
        "facts": facts,
        "fact_n": len(facts),
        "immutable": True,
        "issues_recommendations": False,
    }
    write_json_atomic(pack_path, pack)

    # Update latest validated pointer + merge into warehouse latest index
    write_json_atomic(
        pub / "latest_validated.json",
        {
            "validation_id": report["validation_id"],
            "draft_id": draft.get("draft_id"),
            "path": str(pack_path),
            "approval_status": approval.get("approval_status"),
            "updated_at": now_iso(),
        },
    )

    latest_path = pub / "latest.json"
    latest: dict[str, Any] = {}
    if latest_path.exists():
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
    latest.update(
        {
            "ticker": ticker,
            "engine": "financial_statements_engine",
            "updated_at": now_iso(),
            "latest_validation_id": report["validation_id"],
            "latest_validated_path": str(pack_path),
            "validation_status": approval.get("approval_status"),
            "quality_grade": (report.get("quality_score") or {}).get("grade"),
            "issues_recommendations": False,
        }
    )
    # Keep statements list if present from legacy publisher
    latest.setdefault("statements", latest.get("statements") or [])
    write_json_atomic(latest_path, latest)

    # FSE-06 Financial Warehouse — permanent system of record
    warehouse_result = None
    try:
        from financial_statements_engine.financial_warehouse.publisher.publish import publish_validated_pack

        warehouse_result = publish_validated_pack(validated_pack=pack, draft=draft)
    except Exception as exc:  # pragma: no cover - surface failure without mutating drafts
        warehouse_result = {"ok": False, "published": False, "error": str(exc)}

    return {
        "ok": True,
        "published": True,
        "validation_id": report["validation_id"],
        "fact_n": len(facts),
        "path": str(pack_path),
        "approval_status": approval.get("approval_status"),
        "facts": facts,
        "warehouse": warehouse_result,
    }


def quarantine_draft(draft: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    ticker = str(draft.get("ticker") or "UNKNOWN").upper().strip()
    qdir = ensure_dirs() / "parsing" / "validation" / "quarantine" / ticker
    qdir.mkdir(parents=True, exist_ok=True)
    path = qdir / f"{report['validation_id'].replace(':', '_')}.json"
    write_json_atomic(
        path,
        {
            "draft_id": draft.get("draft_id"),
            "validation_id": report["validation_id"],
            "approval": report.get("approval"),
            "critical_errors": report.get("critical_errors"),
            "errors": report.get("errors"),
            "quarantined_at": now_iso(),
        },
    )
    return {"ok": True, "quarantined": True, "path": str(path)}
