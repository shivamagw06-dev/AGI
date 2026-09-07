"""Immutable audit log for Knowledge Operations actions."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_AUDIT: List[Dict[str, Any]] = []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def record_audit(
    action: str,
    *,
    actor: Optional[str] = None,
    ticker: Optional[str] = None,
    document_hash: Optional[str] = None,
    document_type: Optional[str] = None,
    knowledge_version: Optional[str] = None,
    evidence_ids: Optional[List[str]] = None,
    claims_created: Optional[int] = None,
    research_updated: Optional[bool] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    entry = {
        "audit_id": f"koc_aud_{uuid.uuid4().hex[:12]}",
        "action": action,
        "actor": actor or "system",
        "ticker": (ticker or "").upper() or None,
        "when": _now(),
        "document_hash": document_hash,
        "document_type": document_type,
        "knowledge_version": knowledge_version,
        "evidence_ids": list(evidence_ids or []),
        "claims_created": claims_created,
        "research_updated": research_updated,
        "details": details or {},
        "immutable": True,
    }
    with _LOCK:
        _AUDIT.append(entry)
        # Keep bounded in-process history
        if len(_AUDIT) > 2000:
            del _AUDIT[: len(_AUDIT) - 2000]
    return entry


def list_audit(*, limit: int = 100, ticker: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        rows = list(_AUDIT)
    if ticker:
        t = ticker.upper()
        rows = [r for r in rows if r.get("ticker") == t]
    rows = list(reversed(rows))[: max(1, min(limit, 500))]
    return {"ok": True, "count": len(rows), "entries": rows}
