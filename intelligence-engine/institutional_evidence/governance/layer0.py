"""Layer 0 — Data Governance. Nothing enters AGI without governance."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema import AUTHORITY_SCORES, FRESHNESS_SLA_DAYS


GOVERNANCE_FIELDS = (
    "provider_id",
    "license_usage_policy",
    "source_authority",
    "freshness_sla_days",
    "hash",
    "version",
    "retry_policy",
    "quality_score",
    "provenance_chain",
)


def governance_required_fields() -> List[str]:
    return list(GOVERNANCE_FIELDS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_payload(payload: Dict[str, Any]) -> str:
    blob = repr(sorted((payload or {}).items())).encode("utf-8", errors="replace")
    return hashlib.sha256(blob).hexdigest()


def govern_inbound_dataset(
    payload: Dict[str, Any],
    *,
    provider_id: str,
    document_type: str = "other",
    license_usage_policy: str = "internal_research_only",
    url: str = "",
    entity_id: Optional[str] = None,
    prior_provenance: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Stamp every inbound dataset with governance metadata.

    Rejects anonymous / ungoverened ingress (missing provider or hash).
    """
    provider = str(provider_id or "").strip().lower()
    if not provider:
        return {
            "ok": False,
            "admitted": False,
            "reason": "provider_id required — nothing enters AGI without governance",
        }

    dtype = str(document_type or "other")
    h = payload.get("hash") or payload.get("checksum") or _hash_payload(
        {
            "provider": provider,
            "document_type": dtype,
            "url": url,
            "keys": sorted((payload or {}).keys())[:40],
        }
    )
    authority = float(AUTHORITY_SCORES.get(provider, AUTHORITY_SCORES.get(dtype, 0.4)))
    sla = int(FRESHNESS_SLA_DAYS.get(dtype, 90))
    provenance = list(prior_provenance or [])
    provenance.append(
        {
            "step": "data_governance",
            "provider_id": provider,
            "at": _now(),
            "url": url or None,
            "entity_id": entity_id,
        }
    )

    record = {
        "governance_id": f"gov_{uuid.uuid4().hex[:16]}",
        "provider_id": provider,
        "license_usage_policy": license_usage_policy,
        "source_authority": authority,
        "freshness_sla_days": sla,
        "hash": h,
        "version": int(payload.get("version") or 1),
        "retry_policy": {
            "max_attempts": 3,
            "backoff_seconds": [30, 120, 600],
            "retry_on": ["timeout", "5xx", "rate_limit"],
        },
        "quality_score": None,  # filled by Data Quality Engine
        "provenance_chain": provenance,
        "document_type": dtype,
        "entity_id": entity_id,
        "admitted_at": _now(),
        "layer": 0,
        "rule": "Nothing enters AGI without governance",
    }
    missing = [f for f in GOVERNANCE_FIELDS if record.get(f) is None and f != "quality_score"]
    return {
        "ok": len(missing) == 0,
        "admitted": len(missing) == 0,
        "governance": record,
        "missing_fields": missing,
        "next": "evidence_acquisition" if not missing else "reject",
    }
