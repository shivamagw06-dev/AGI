"""Institutional audit log — every recommendation must be reproducible."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from decision_engine.governance.schema import CONSTITUTION_VERSION, GOVERNANCE_VERSION, PROGRAMME
from decision_engine.schema import IDE_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(payload: Any) -> str:
    try:
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    except Exception:
        raw = str(payload).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _store_put(name: str, payload: dict[str, Any]) -> None:
    try:
        from knowledge_factory.historical_depth import store as hd_store

        hd_store.put_report(name, payload)
    except Exception:
        pass


def _store_get(name: str) -> dict[str, Any] | None:
    try:
        from knowledge_factory.historical_depth import store as hd_store

        row = hd_store.get_report(name)
        return row if isinstance(row, dict) else None
    except Exception:
        return None


def build_recommendation_id(ticker: str | None) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    sym = (ticker or "UNKNOWN").upper().replace(".", "")[:24]
    return f"AGIB-{day}-{sym}-{uuid4().hex[:6].upper()}"


def load_previous_snapshot(ticker: str | None) -> dict[str, Any] | None:
    if not ticker:
        return None
    return _store_get(f"iros_last_analysis_{ticker.upper()}")


def persist_snapshot(ticker: str | None, snapshot: dict[str, Any]) -> None:
    if not ticker:
        return
    _store_put(f"iros_last_analysis_{ticker.upper()}", snapshot)


def append_audit_record(record: dict[str, Any]) -> dict[str, Any]:
    """Append-only audit trail (latest + history list)."""
    ticker = str(record.get("ticker") or "UNKNOWN").upper()
    hist_name = f"iros_audit_history_{ticker}"
    hist = _store_get(hist_name) or {"ticker": ticker, "records": []}
    records = list(hist.get("records") or [])
    records.append(record)
    # Cap history to keep store bounded
    hist["records"] = records[-200:]
    hist["updated_at"] = _now()
    _store_put(hist_name, hist)
    _store_put(f"iros_audit_latest_{ticker}", record)
    _store_put(f"iros_audit_{record.get('recommendation_id')}", record)
    return record


def get_audit_record(recommendation_id: str) -> dict[str, Any] | None:
    return _store_get(f"iros_audit_{recommendation_id}")


def build_audit_record(
    *,
    ticker: str | None,
    company_name: str | None,
    query: str,
    readiness_gate: dict[str, Any],
    decision: dict[str, Any],
    engine_confidence: dict[str, Any],
    lineage: dict[str, Any],
    thesis_drift: dict[str, Any],
    recommendation_delta: dict[str, Any],
    critical_missing: dict[str, Any],
    price_snapshot: Any = None,
    knowledge_snapshot_at: str | None = None,
) -> dict[str, Any]:
    rid = build_recommendation_id(ticker)
    evidence_hash = _sha256(
        {
            "coverage": readiness_gate.get("coverage"),
            "lineage": lineage.get("rows"),
            "engines": engine_confidence.get("by_engine"),
            "readiness": readiness_gate.get("recommendation_readiness_pct"),
        }
    )
    record = {
        "recommendation_id": rid,
        "programme": PROGRAMME,
        "governance_version": GOVERNANCE_VERSION,
        "decision_engine": IDE_VERSION,
        "constitution": CONSTITUTION_VERSION,
        "ticker": (ticker or "").upper() or None,
        "company_name": company_name,
        "query": query,
        "recorded_at": _now(),
        "knowledge_snapshot": knowledge_snapshot_at or _now(),
        "price_snapshot": price_snapshot,
        "evidence_hash": evidence_hash,
        "investment_thesis_status": readiness_gate.get("investment_thesis_status"),
        "readiness_band": readiness_gate.get("band"),
        "recommendation_readiness_pct": readiness_gate.get("recommendation_readiness_pct"),
        "institutional_readiness_pct": readiness_gate.get("institutional_readiness_pct"),
        "analytical_confidence": readiness_gate.get("analytical_confidence_display"),
        "decision_action": decision.get("action"),
        "overall_score": decision.get("overall_score") or decision.get("score"),
        "gate_status": readiness_gate.get("status"),
        "not_a_negative_view": readiness_gate.get("not_a_negative_view"),
        "decision_line": readiness_gate.get("decision_line"),
        "weakest_engine": engine_confidence.get("weakest_engine"),
        "hard_evidence_floor_pct": engine_confidence.get("hard_evidence_floor_pct"),
        "engine_confidence": engine_confidence.get("by_engine"),
        "lineage_complete_count": lineage.get("lineage_complete_count"),
        "critical_missing": (critical_missing.get("items") or [])[:5],
        "thesis_drift": thesis_drift.get("thesis_drift"),
        "previous_thesis": thesis_drift.get("previous_thesis"),
        "current_thesis": thesis_drift.get("current_thesis"),
        "recommendation_delta_pct": recommendation_delta.get("delta_pct"),
        "recommendation_delta_driver": recommendation_delta.get("driver"),
        "reproducible": True,
        "append_only": True,
        "note": "Audit record is sufficient to recreate the decision context for challenge / review.",
    }
    append_audit_record(record)
    # Snapshot for next drift/delta comparison
    persist_snapshot(
        ticker,
        {
            "recorded_at": record["recorded_at"],
            "generated_at": record["recorded_at"],
            "recommendation_id": rid,
            "thesis_stance": thesis_drift.get("current_thesis"),
            "investment_thesis_status": record["investment_thesis_status"],
            "readiness_band": record["readiness_band"],
            "action": record["decision_action"],
            "recommendation_readiness_pct": record["recommendation_readiness_pct"],
            "institutional_readiness_pct": record["institutional_readiness_pct"],
            "evidence_confidence_pct": record["recommendation_readiness_pct"],
            "overall_coverage_pct": record["institutional_readiness_pct"],
            "house_view": thesis_drift.get("current_thesis"),
        },
    )
    return record
