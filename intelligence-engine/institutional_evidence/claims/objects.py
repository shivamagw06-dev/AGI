"""Claim Objects — every material research sentence maps to evidence."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any, Dict, List, Optional

from ..schema import FORBIDDEN_INVENTED_FIELDS


def build_claim(
    text: str,
    *,
    entity_id: str,
    ticker: str,
    evidence_ids: Optional[List[str]] = None,
    primary_source: Optional[str] = None,
    confidence: Optional[float] = None,
    consumers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    t = str(text or "").strip()
    evid = list(evidence_ids or [])
    verified = bool(evid) and bool(primary_source)
    conf = float(confidence) if confidence is not None else (96.0 if verified else 0.0)
    cid = f"claim_{hashlib.sha256(t.encode('utf-8')).hexdigest()[:16]}"
    return {
        "claim_id": cid,
        "text": t,
        "entity_id": entity_id,
        "ticker": ticker.upper(),
        "evidence_ids": evid,
        "primary_source": primary_source,
        "confidence": conf,
        "verified": verified,
        "consumers": list(consumers or []),
        "unsupported": not verified,
        "schema": "ClaimObject.v1",
        "rule": "Research becomes a graph of verified claims",
    }


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def extract_claims_from_note(
    note_text: str,
    *,
    entity_id: str,
    ticker: str,
    evidence_ids: Optional[List[str]] = None,
    primary_source: Optional[str] = None,
) -> Dict[str, Any]:
    """Naive sentence → claim extraction for lifecycle/observability."""
    text = str(note_text or "").strip()
    if not text:
        return {"ok": True, "claims": [], "unsupported_count": 0}
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if len(s.strip()) > 20]
    claims = []
    for s in sentences:
        # Material if touches forbidden inventable fields or looks quantitative
        material = any(f in s.lower() for f in FORBIDDEN_INVENTED_FIELDS) or bool(
            re.search(r"\d+(\.\d+)?%?", s)
        )
        if not material:
            continue
        claims.append(
            build_claim(
                s,
                entity_id=entity_id,
                ticker=ticker,
                evidence_ids=evidence_ids,
                primary_source=primary_source,
                consumers=["research_note"],
            )
        )
    unsupported = sum(1 for c in claims if c.get("unsupported"))
    return {
        "ok": True,
        "claim_count": len(claims),
        "unsupported_count": unsupported,
        "claims": claims,
        "zero_unsupported_material_claims": unsupported == 0,
    }


def verify_claims(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    unsupported = [c for c in claims if not c.get("verified")]
    return {
        "ok": True,
        "total": len(claims),
        "verified": len(claims) - len(unsupported),
        "unsupported": len(unsupported),
        "zero_unsupported_material_claims": len(unsupported) == 0,
        "unsupported_claims": unsupported[:50],
    }
