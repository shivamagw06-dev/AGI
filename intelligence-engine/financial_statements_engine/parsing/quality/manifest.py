"""Immutable Parse Manifest — mandatory audit record for every parse."""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


def new_manifest_id() -> str:
    return f"pm:{uuid.uuid4().hex[:20]}"


def new_draft_id() -> str:
    return f"draft:{uuid.uuid4().hex[:20]}"


def document_hash(data: bytes) -> str:
    return hashlib.sha256(data or b"").hexdigest()


def build_manifest(
    *,
    draft_id: str,
    document_hash: str,
    company_id: str,
    ticker: str,
    parser_name: str,
    parser_version: str,
    schema_version: str,
    metric_registry_version: str,
    pne_version: str,
    processing_time_ms: float,
    document_type: str,
    source: str | None,
    reporting_period: dict[str, Any] | None,
    currency_detected: str | None,
    unit_detected: Any,
    sections_found: list[str],
    metrics_extracted: list[str],
    metrics_unknown: list[str],
    metrics_missing: list[str] | None = None,
    warnings: list[Any] | None = None,
    errors: list[Any] | None = None,
    confidence: dict[str, Any] | None = None,
    hierarchy_fingerprint: str | None = None,
    deterministic_fingerprint: str | None = None,
    lineage_root_id: str | None = None,
    replay_of: str | None = None,
    manifest_id: str | None = None,
) -> dict[str, Any]:
    mid = manifest_id or new_manifest_id()
    return {
        "manifest_id": mid,
        "draft_id": draft_id,
        "document_hash": document_hash,
        "company_id": company_id,
        "ticker": ticker.upper().strip(),
        "parser_name": parser_name,
        "parser_version": parser_version,
        "schema_version": schema_version,
        "metric_registry_version": metric_registry_version,
        "pne_version": pne_version,
        "parse_timestamp": now_iso(),
        "processing_time_ms": round(float(processing_time_ms), 3),
        "document_type": document_type,
        "source": source,
        "reporting_period": reporting_period or {},
        "currency_detected": currency_detected,
        "unit_detected": unit_detected,
        "sections_found": list(sections_found or []),
        "metrics_extracted": list(metrics_extracted or []),
        "metrics_extracted_n": len(metrics_extracted or []),
        "metrics_unknown": list(metrics_unknown or []),
        "metrics_unknown_n": len(metrics_unknown or []),
        "metrics_missing": list(metrics_missing or []),
        "warnings": list(warnings or []),
        "errors": list(errors or []),
        "confidence": confidence or {},
        "hierarchy_fingerprint": hierarchy_fingerprint,
        "deterministic_fingerprint": deterministic_fingerprint,
        "lineage_root_id": lineage_root_id,
        "replay_of": replay_of,
        "immutable": True,
        "object": "parse_manifest",
        "workstream_id": "FSE-04.1",
    }


def store_manifest(manifest: dict[str, Any]) -> Path:
    """Write-once store. Refuses overwrite of existing manifest_id."""
    ticker = str(manifest["ticker"]).upper()
    mid = str(manifest["manifest_id"])
    path = ensure_dirs() / "parsing" / "manifests" / ticker / f"{mid.replace(':', '_')}.json"
    if path.exists():
        raise FileExistsError(f"manifest_immutable_violation: {mid}")
    write_json_atomic(path, manifest)
    # index latest pointer (pointer only — history retained)
    idx = ensure_dirs() / "parsing" / "manifests" / ticker / "latest.json"
    write_json_atomic(
        idx,
        {
            "ticker": ticker,
            "manifest_id": mid,
            "draft_id": manifest.get("draft_id"),
            "path": str(path),
            "updated_at": now_iso(),
        },
    )
    return path


def load_manifest(ticker: str, manifest_id: str) -> dict[str, Any] | None:
    path = ensure_dirs() / "parsing" / "manifests" / ticker.upper() / f"{manifest_id.replace(':', '_')}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_manifests(ticker: str) -> list[dict[str, Any]]:
    d = ensure_dirs() / "parsing" / "manifests" / ticker.upper()
    if not d.exists():
        return []
    rows = []
    for p in sorted(d.glob("pm_*.json")) + sorted(d.glob("pm*.json")):
        if p.name == "latest.json":
            continue
        try:
            rows.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    # also match pm_ hex files from replace
    for p in sorted(d.glob("*.json")):
        if p.name == "latest.json":
            continue
        try:
            row = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if row.get("manifest_id") and row not in rows:
            rows.append(row)
    return rows
