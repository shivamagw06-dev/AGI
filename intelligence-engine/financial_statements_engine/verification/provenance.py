"""Workflow provenance / lineage page (FSE-02.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.orchestrator.store import load_workflow
from financial_statements_engine.store import ensure_dirs, paths_for
from financial_statements_engine.util import now_iso
from financial_statements_engine.verification.schema import VERSION, WORKSTREAM_ID
from financial_statements_engine.verification.store import save_provenance


def _raw_node(wf: dict[str, Any]) -> dict[str, Any]:
    ticker = str(wf.get("ticker") or "").upper()
    eid = str(wf.get("evidence_id") or "")
    meta_path = None
    bytes_path = None
    if ticker and eid:
        digest = eid.removeprefix("sha256:")
        mp = paths_for(ticker)["raw_meta"] / f"{digest}.json"
        if mp.exists():
            meta_path = str(mp)
            try:
                meta = json.loads(mp.read_text(encoding="utf-8"))
                bytes_path = meta.get("bytes_path")
            except json.JSONDecodeError:
                pass
    return {
        "node": "raw_evidence",
        "evidence_id": eid or None,
        "document_hash": wf.get("document_hash"),
        "meta_path": meta_path,
        "bytes_path": bytes_path,
        "present": bool(meta_path or wf.get("inline_bytes_b64") or eid),
    }


def _parse_node(wf: dict[str, Any]) -> dict[str, Any]:
    arts = wf.get("artifacts") or {}
    ticker = str(wf.get("ticker") or "").upper()
    draft_id = arts.get("draft_id")
    manifest_id = None
    draft = arts.get("draft") if isinstance(arts.get("draft"), dict) else None
    if isinstance(draft, dict):
        manifest_id = draft.get("manifest_id")
        draft_id = draft_id or draft.get("draft_id")
    latest = ensure_dirs() / "parsing" / "drafts" / ticker / "latest.json"
    return {
        "node": "parse_manifest",
        "draft_id": draft_id,
        "manifest_id": manifest_id,
        "latest_pointer": str(latest) if latest.exists() else None,
        "present": bool(draft_id or (latest.exists())),
    }


def _coverage_node(wf: dict[str, Any]) -> dict[str, Any]:
    ticker = str(wf.get("ticker") or "").upper()
    arts = wf.get("artifacts") or {}
    draft = arts.get("draft") if isinstance(arts.get("draft"), dict) else {}
    coverage_id = draft.get("coverage_matrix_id") or draft.get("coverage_id")
    matrices = ensure_dirs() / "parsing" / "coverage" / ticker
    present = bool(coverage_id) or (matrices.is_dir() and any(matrices.glob("*.json")))
    return {
        "node": "coverage_matrix",
        "coverage_id": coverage_id,
        "dir": str(matrices) if matrices.is_dir() else None,
        "present": present,
    }


def _validation_node(wf: dict[str, Any]) -> dict[str, Any]:
    arts = wf.get("artifacts") or {}
    vid = arts.get("validation_id")
    ticker = str(wf.get("ticker") or "").upper()
    reports = ensure_dirs() / "validation" / "reports" / ticker
    present = bool(vid) or (reports.is_dir() and any(reports.glob("*.json")))
    return {
        "node": "validation_report",
        "validation_id": vid,
        "approval_status": (arts.get("validated_pack") or {}).get("approval_status")
        or ((arts.get("validated_pack") or {}).get("approval") or {}).get("approval_status"),
        "reports_dir": str(reports) if reports.is_dir() else None,
        "present": present,
    }


def _warehouse_node(wf: dict[str, Any]) -> dict[str, Any]:
    arts = wf.get("artifacts") or {}
    pub = arts.get("publish_result") if isinstance(arts.get("publish_result"), dict) else {}
    ticker = str(wf.get("ticker") or "").upper()
    published = paths_for(ticker)["published"]
    version = pub.get("version") or pub.get("statement_version") or pub.get("warehouse_version")
    return {
        "node": "warehouse_version",
        "published": bool(pub.get("published")),
        "version": version,
        "publish_result_keys": sorted(pub.keys())[:20] if pub else [],
        "published_dir": str(published) if published.is_dir() else None,
        "present": bool(pub.get("published")) or (published.is_dir() and any(published.glob("*.json"))),
    }


def _dme_node(wf: dict[str, Any]) -> dict[str, Any]:
    ticker = str(wf.get("ticker") or "").upper()
    company_id = str(wf.get("company_id") or f"nse:{ticker}")
    versions: list[Any] = []
    try:
        from financial_statements_engine.derived_metrics.store.versions import list_company_metrics

        versions = list_company_metrics(company_id) or []
    except Exception:
        versions = []
    der = paths_for(ticker)["derived"]
    present = bool(versions) or (der.is_dir() and any(der.glob("*.json")))
    return {
        "node": "derived_metrics_version",
        "company_id": company_id,
        "versions_n": len(versions) if isinstance(versions, list) else 0,
        "latest": versions[0] if isinstance(versions, list) and versions else None,
        "derived_dir": str(der) if der.is_dir() else None,
        "present": present,
    }


def build_provenance(wf: dict[str, Any]) -> dict[str, Any]:
    chain = [
        {
            "node": "workflow",
            "workflow_id": wf.get("workflow_id"),
            "state": wf.get("state"),
            "ticker": wf.get("ticker"),
            "period": wf.get("period"),
            "present": True,
        },
        _raw_node(wf),
        _parse_node(wf),
        _coverage_node(wf),
        _validation_node(wf),
        _warehouse_node(wf),
        _dme_node(wf),
    ]
    return {
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "workflow_id": wf.get("workflow_id"),
        "company": wf.get("ticker"),
        "period": wf.get("period"),
        "lineage": chain,
        "lineage_complete": all(n.get("present") for n in chain if n["node"] in ("workflow", "raw_evidence", "parse_manifest", "validation_report", "warehouse_version", "derived_metrics_version")),
        "generated_at": now_iso(),
    }


def generate_provenance(workflow_id: str, *, persist: bool = True) -> dict[str, Any]:
    wf = load_workflow(workflow_id)
    if not wf:
        return {"ok": False, "error": "workflow_not_found", "workflow_id": workflow_id}
    page = build_provenance(wf)
    path = None
    if persist:
        path = str(save_provenance(page))
    return {"ok": True, "provenance": page, "path": path}
