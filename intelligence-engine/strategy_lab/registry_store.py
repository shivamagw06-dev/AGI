"""Best-effort Supabase persistence for Validation Registry decisions."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any
from urllib import error, parse, request

_LOCK = threading.Lock()
_LAST_WRITE: dict[str, Any] = {"at": 0.0, "result": {"ok": False, "status": "NOT_RUN"}}
_WRITE_TTL_SECONDS = 300
_EVIDENCE_CACHE: dict[str, Any] = {"at": 0.0, "rows": {}}


def _credentials() -> tuple[str, str] | None:
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").strip().rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    return (url, key) if url and key else None


def _rest(method: str, table: str, *, query: str = "", body: Any = None, prefer: str = "return=minimal") -> Any:
    credentials = _credentials()
    if not credentials:
        raise RuntimeError("SUPABASE_CREDENTIALS_MISSING")
    url, key = credentials
    data = None if body is None else json.dumps(body, ensure_ascii=False, default=str).encode("utf-8")
    req = request.Request(
        f"{url}/rest/v1/{table}{query}",
        data=data,
        method=method,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": prefer,
        },
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"SUPABASE_{table.upper()}_{exc.code}: {detail}") from exc


def _receipt(strategy_id: str, version: str, gate: str, evidence: dict[str, Any]) -> str:
    payload = json.dumps(
        {"strategy_id": strategy_id, "version": version, "gate": gate, "evidence": evidence},
        sort_keys=True,
        ensure_ascii=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def table_health() -> dict[str, Any]:
    if not _credentials():
        return {"ok": False, "status": "NOT_CONFIGURED"}
    try:
        rows = _rest("GET", "strategy_validation_registry", query="?select=strategy_key&limit=1") or []
        return {"ok": True, "status": "READY", "sample_rows": len(rows)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": "UNAVAILABLE", "error": str(exc)[:300]}


def load_latest_evidence(*, force: bool = False) -> dict[str, dict[str, dict[str, Any]]]:
    """Load the newest append-only receipt for every strategy gate."""
    now = time.monotonic()
    with _LOCK:
        if not force and now - float(_EVIDENCE_CACHE["at"] or 0) < _WRITE_TTL_SECONDS:
            return _EVIDENCE_CACHE["rows"]
        if not _credentials():
            return {}
        try:
            rows = _rest(
                "GET",
                "strategy_validation_evidence",
                query="?select=strategy_key,strategy_version,gate_key,status,observed_at,source,receipt_id,metrics,limitations,recorded_at&status=neq.MISSING&order=recorded_at.desc&limit=1000",
            ) or []
        except Exception:  # noqa: BLE001
            return {}
        latest: dict[str, dict[str, dict[str, Any]]] = {}
        for row in rows:
            strategy_key = str(row.get("strategy_key") or "")
            gate_key = str(row.get("gate_key") or "")
            # Absence is not a new validation finding. Runtime refreshes must
            # not shadow an older substantive receipt with MISSING.
            if str(row.get("status") or "MISSING").upper() == "MISSING":
                continue
            if not strategy_key or not gate_key or gate_key in latest.setdefault(strategy_key, {}):
                continue
            metrics = row.get("metrics") or {}
            latest[strategy_key][gate_key] = {
                "status": row.get("status", "MISSING"),
                "observed_at": row.get("observed_at"),
                "source": row.get("source"),
                "receipt_id": row.get("receipt_id"),
                "detail": metrics.get("detail", metrics),
            }
        _EVIDENCE_CACHE.update({"at": now, "rows": latest})
        return latest


def append_validation_evidence(strategy_id: str, version: str, evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Append independently hashed receipts produced by a validation run."""
    rows = []
    for gate, item in evidence.items():
        receipt_id = _receipt(strategy_id, version, gate, item)
        rows.append({
            "strategy_key": strategy_id,
            "strategy_version": version,
            "gate_key": gate,
            "status": item.get("status", "MISSING"),
            "observed_at": item.get("observed_at"),
            "source": item.get("source", "strategy_lab.backtest"),
            "source_version": item.get("source_version"),
            "receipt_id": receipt_id,
            "metrics": {"detail": item.get("detail")},
            "limitations": item.get("limitations") or [],
            "evidence_hash": receipt_id,
        })
    try:
        if rows:
            _rest("POST", "strategy_validation_evidence", body=rows)
        _EVIDENCE_CACHE.update({"at": 0.0, "rows": {}})
        return {"ok": True, "status": "PERSISTED", "evidence_rows": len(rows), "receipt_ids": [row["receipt_id"] for row in rows]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": "PERSISTENCE_FAILED", "error": str(exc)[:300], "evidence_rows": 0}


def persist_decisions(strategies: list[dict[str, Any]], *, force: bool = False) -> dict[str, Any]:
    now = time.monotonic()
    with _LOCK:
        if not force and now - float(_LAST_WRITE["at"] or 0) < _WRITE_TTL_SECONDS:
            return {**_LAST_WRITE["result"], "cached": True}
        decisions = []
        evidence_rows = []
        for strategy in strategies:
            decision = strategy.get("validation_registry") or {}
            strategy_id = str(strategy.get("strategy_id") or decision.get("strategy_id") or "")
            version = str(strategy.get("version") or "unknown")
            if not strategy_id or not decision:
                continue
            decisions.append({
                "strategy_key": strategy_id,
                "strategy_name": str(strategy.get("name") or strategy_id),
                "strategy_version": version,
                "requested_lifecycle": decision.get("requested_lifecycle", "EXPERIMENTAL"),
                "supported_lifecycle": decision.get("supported_lifecycle", "EXPERIMENTAL"),
                "effective_lifecycle": decision.get("lifecycle", "EXPERIMENTAL"),
                "current_health": decision.get("health", "DEGRADED"),
                "health_reason": decision.get("health_reason"),
                "allowed_use": decision.get("allowed_use", "Research only"),
                "execution_status": decision.get("execution", "BLOCKED"),
                "historical_claims_allowed": bool(decision.get("historical_alpha_claims_allowed")),
                "automatic_demotion": bool(decision.get("automatic_demotion")),
                "registry_version": decision.get("registry_version"),
                "decision": decision,
                "evaluated_at": decision.get("evaluated_at"),
            })
            for gate, evidence in (decision.get("evidence") or {}).items():
                if str(evidence.get("status") or "MISSING").upper() == "MISSING":
                    continue
                receipt_id = _receipt(strategy_id, version, gate, evidence)
                evidence_rows.append({
                    "strategy_key": strategy_id,
                    "strategy_version": version,
                    "gate_key": gate,
                    "status": evidence.get("status", "MISSING"),
                    "observed_at": evidence.get("observed_at"),
                    "source": evidence.get("source"),
                    "receipt_id": receipt_id,
                    "metrics": {"detail": evidence.get("detail")},
                    "limitations": [],
                    "evidence_hash": receipt_id,
                })
        try:
            if decisions:
                _rest(
                    "POST",
                    "strategy_validation_registry",
                    query="?on_conflict=strategy_key",
                    body=decisions,
                    prefer="resolution=merge-duplicates,return=minimal",
                )
            if evidence_rows:
                _rest("POST", "strategy_validation_evidence", body=evidence_rows)
            result = {"ok": True, "status": "PERSISTED", "decisions": len(decisions), "evidence_rows": len(evidence_rows)}
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "status": "PERSISTENCE_FAILED", "error": str(exc)[:300], "decisions": 0, "evidence_rows": 0}
        _LAST_WRITE.update({"at": now, "result": result})
        return result
