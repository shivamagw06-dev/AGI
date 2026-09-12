"""Evidence Registry — immutable evidence objects with authority, freshness, hash."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema import AUTHORITY_SCORES, FRESHNESS_SLA_DAYS, PRIMARY_DOCUMENT_TYPES


# Process-local immutable registry (v1); durable store can replace later.
_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _age_days(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0)
    except Exception:
        return None


class EvidenceRegistry:
    """Immutable evidence index keyed by evidence_id."""

    def __init__(self) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}

    def upsert_immutable(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        eid = str(obj.get("evidence_id") or "")
        if not eid:
            raise ValueError("evidence_id required")
        if eid in self._items:
            # Immutable: return existing; do not overwrite
            return dict(self._items[eid])
        frozen = dict(obj)
        frozen["immutable"] = True
        frozen["registered_at"] = _now()
        self._items[eid] = frozen
        return dict(frozen)

    def get(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        item = self._items.get(evidence_id)
        return dict(item) if item else None

    def for_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        t = ticker.upper()
        return [dict(v) for v in self._items.values() if str(v.get("ticker", "")).upper() == t]

    def to_dict(self) -> Dict[str, Any]:
        return {"count": len(self._items), "items": list(self._items.values())}


def _make_evidence_id(doc: Dict[str, Any]) -> str:
    h = doc.get("hash") or doc.get("checksum") or ""
    if not h:
        blob = json.dumps(
            {k: doc.get(k) for k in ("ticker", "document_type", "source", "url")},
            sort_keys=True,
        )
        h = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"ev_{str(h)[:24]}"


def register_documents(acquisition: Dict[str, Any]) -> Dict[str, Any]:
    """Register acquired documents into the immutable evidence registry."""
    ticker = str(acquisition.get("ticker") or "").upper()
    company = str(acquisition.get("company") or ticker)
    docs = acquisition.get("documents") or []
    if ticker not in _REGISTRY:
        _REGISTRY[ticker] = {}

    registered: List[Dict[str, Any]] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        dtype = str(doc.get("document_type") or "unknown")
        source = str(doc.get("source") or "unknown")
        authority = float(AUTHORITY_SCORES.get(source, AUTHORITY_SCORES.get(dtype, 0.4)))
        age = _age_days(doc.get("published_at") or doc.get("downloaded_at"))
        sla = FRESHNESS_SLA_DAYS.get(dtype, 90)
        fresh = age is None or age <= sla
        h = doc.get("hash") or doc.get("checksum")
        if not h:
            continue  # CI gate: evidence hash missing → skip (fail closed for that doc)
        eid = _make_evidence_id(doc)
        obj = {
            "evidence_id": eid,
            "company": company,
            "ticker": ticker,
            "source": source,
            "authority_score": authority,
            "freshness_days": age,
            "freshness_ok": fresh,
            "freshness_sla_days": sla,
            "hash": h,
            "version": 1,
            "period": doc.get("published_at"),
            "document_type": dtype,
            "confidence": min(1.0, authority * (1.0 if fresh else 0.6)),
            "linked_claims": [],
            "consumers": [],
            "research_ready": bool(
                dtype in PRIMARY_DOCUMENT_TYPES and fresh and h and authority >= 0.7
            ),
            "document_id": doc.get("document_id"),
            "url": doc.get("url"),
            "status": doc.get("status"),
        }
        if eid not in _REGISTRY[ticker]:
            _REGISTRY[ticker][eid] = obj
        registered.append(dict(_REGISTRY[ticker][eid]))

    items = list(_REGISTRY.get(ticker, {}).values())
    primary = [i for i in items if i.get("document_type") in PRIMARY_DOCUMENT_TYPES]
    return {
        "ok": True,
        "ticker": ticker,
        "company": company,
        "evidence_count": len(items),
        "newly_registered": len(registered),
        "primary_count": len(primary),
        "research_ready_objects": sum(1 for i in items if i.get("research_ready")),
        "missing_hash_skipped": sum(
            1 for d in docs if isinstance(d, dict) and not (d.get("hash") or d.get("checksum"))
        ),
        "items": items,
        "immutable": True,
    }


def get_registry_for_ticker(ticker: str) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    items = list(_REGISTRY.get(t, {}).values())
    if not items:
        # Lazy: acquire + register
        try:
            from ..acquisition.collector import acquire_company_documents

            acq = acquire_company_documents(t)
            return register_documents(acq)
        except Exception as exc:
            return {"ok": False, "ticker": t, "error": str(exc), "items": []}
    return {
        "ok": True,
        "ticker": t,
        "evidence_count": len(items),
        "items": items,
        "immutable": True,
    }
