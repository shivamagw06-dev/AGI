"""Service-role persistence for governed financial valuation knowledge."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable
from urllib import error, request

from financials_valuation.banking import BANKING_MODEL

Transport = Callable[..., Any]


def _credentials() -> tuple[str, str] | None:
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return (url, key) if url and key else None


def _rest(method: str, table: str, *, query: str = "", body: Any = None,
          prefer: str = "return=minimal", timeout: float = 20) -> Any:
    credentials = _credentials()
    if not credentials:
        raise RuntimeError("SUPABASE_CREDENTIALS_MISSING")
    url, key = credentials
    data = None if body is None else json.dumps(body, sort_keys=True, default=str).encode("utf-8")
    req = request.Request(f"{url}/rest/v1/{table}{query}", data=data, method=method, headers={
        "apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": prefer,
    })
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"SUPABASE_{table.upper()}_{exc.code}:{detail}") from exc


def _hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def seed_banking_model(*, transport: Transport = _rest) -> dict[str, Any]:
    """Idempotently persist the code-reviewed bank curriculum and immutable version."""
    payload = BANKING_MODEL.to_dict()
    digest = _hash(payload)
    now = datetime.now(timezone.utc).isoformat()
    transport("POST", "sector_valuation_models", query="?on_conflict=sector_id", body={
        "sector_id": BANKING_MODEL.sector_id,
        "sector_name": BANKING_MODEL.sector_name,
        "parent_sector": "FINANCIALS",
        "subsector": BANKING_MODEL.subsector,
        "active_version": BANKING_MODEL.version,
        "validation_status": BANKING_MODEL.validation_status,
        "confidence": BANKING_MODEL.confidence,
        "effective_date": BANKING_MODEL.effective_date,
        "updated_at": now,
    }, prefer="resolution=merge-duplicates,return=minimal")
    transport("POST", "sector_valuation_model_versions", query="?on_conflict=sector_id,version", body={
        "sector_id": BANKING_MODEL.sector_id,
        "version": BANKING_MODEL.version,
        "model_payload": payload,
        "content_hash": digest,
        "created_by": "agi-code-reviewed-model",
    }, prefer="resolution=ignore-duplicates,return=minimal")
    return {"ok": True, "sector_id": BANKING_MODEL.sector_id, "version": BANKING_MODEL.version,
            "content_hash": digest, "validation_status": BANKING_MODEL.validation_status,
            "certified": False, "execution_eligible": False}


def persist_evidence(evidence: dict[str, Any], *, transport: Transport = _rest) -> dict[str, Any]:
    required = ("knowledge_key", "source_type", "source_id", "available_at")
    missing = [key for key in required if not evidence.get(key)]
    if missing:
        return {"ok": False, "status": "DATA_UNAVAILABLE", "missing": missing}
    payload = {
        "sector_id": BANKING_MODEL.sector_id, "version": BANKING_MODEL.version,
        "knowledge_key": evidence["knowledge_key"], "source_type": evidence["source_type"],
        "source_id": evidence["source_id"], "source_date": evidence.get("source_date"),
        "available_at": evidence["available_at"], "evidence_payload": evidence.get("evidence_payload") or {},
        "validation_status": evidence.get("validation_status") or "PROPOSED",
        "confidence": float(evidence.get("confidence") or 0),
    }
    if not 0 <= payload["confidence"] <= 1:
        return {"ok": False, "status": "VALIDATION_FAILED", "reason": "confidence_out_of_range"}
    transport("POST", "sector_valuation_evidence",
              query="?on_conflict=sector_id,version,knowledge_key,source_id,available_at", body=payload,
              prefer="resolution=ignore-duplicates,return=minimal")
    return {"ok": True, "status": payload["validation_status"], "knowledge_key": payload["knowledge_key"]}


def persist_certification(result: dict[str, Any], *, transport: Transport = _rest) -> dict[str, Any]:
    status = str(result.get("certification_status") or "NOT_STARTED")
    if status == "PASSED" and not all((result.get("authorized_reviewer"), result.get("reviewer_authorized"), result.get("review_evidence_id"))):
        return {"ok": False, "status": "VALIDATION_FAILED", "reason": "external_review_evidence_required"}
    body = {
        "sector_id": BANKING_MODEL.sector_id, "model_version": BANKING_MODEL.version,
        "certification_status": status, "gates": result.get("gates") or {},
        "passed_gates": int(result.get("passed_gates") or 0), "total_gates": int(result.get("total_gates") or 20),
        "evaluated_companies": sorted((result.get("companies") or {}).keys()),
        "evidence_cutoff": result.get("evidence_cutoff"), "reviewer": result.get("authorized_reviewer"),
        "certified_at": datetime.now(timezone.utc).isoformat() if status == "PASSED" else None,
    }
    transport("POST", "sector_valuation_certifications", body=body, prefer="return=minimal")
    return {"ok": True, "status": status, "automatic_promotion": False}


def table_health(*, transport: Transport = _rest) -> dict[str, Any]:
    try:
        rows = transport("GET", "sector_valuation_models", query="?select=sector_id,active_version,validation_status&limit=5") or []
        return {"ok": True, "status": "READY", "models": rows}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": "UNAVAILABLE", "error": str(exc)[:300]}
