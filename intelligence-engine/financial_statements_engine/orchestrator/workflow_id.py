"""Workflow identity — company + period + filing_type + document_hash."""

from __future__ import annotations

import hashlib
from typing import Any


def normalize_identity(
    *,
    company_id: str | None = None,
    ticker: str | None = None,
    period: str | None = None,
    filing_type: str | None = None,
    document_hash: str | None = None,
    evidence_id: str | None = None,
) -> dict[str, str]:
    t = (ticker or "").upper().strip()
    cid = (company_id or (f"nse:{t}" if t else "nse:UNKNOWN")).strip()
    per = (period or "unknown").strip()
    ftype = (filing_type or "unknown").strip().lower()
    doc = (document_hash or "").strip()
    if not doc and evidence_id:
        doc = str(evidence_id).removeprefix("sha256:")
    if not doc:
        doc = "unknown"
    return {
        "company_id": cid,
        "ticker": t or cid.split(":")[-1],
        "period": per,
        "filing_type": ftype,
        "document_hash": doc,
    }


def make_workflow_id(identity: dict[str, str]) -> str:
    raw = "|".join(
        [
            identity["company_id"],
            identity["period"],
            identity["filing_type"],
            identity["document_hash"],
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"wf:{digest}"


def identity_from_payload(payload: dict[str, Any]) -> dict[str, str]:
    return normalize_identity(
        company_id=payload.get("company_id"),
        ticker=payload.get("ticker"),
        period=payload.get("period") or payload.get("period_end"),
        filing_type=payload.get("filing_type") or payload.get("period_type") or payload.get("document_type"),
        document_hash=payload.get("document_hash") or payload.get("content_sha256"),
        evidence_id=payload.get("evidence_id"),
    )
