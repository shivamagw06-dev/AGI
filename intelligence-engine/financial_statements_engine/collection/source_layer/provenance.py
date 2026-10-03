"""Provenance helpers — full source lineage for raw evidence (FSE-02.3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs
from financial_statements_engine.util import now_iso, write_json_atomic


PROVENANCE_FIELDS = (
    "company_id",
    "company_name",
    "source",
    "filing_type",
    "reporting_period",
    "filing_date",
    "document_hash",
    "download_timestamp",
    "original_filename",
    "mime_type",
    "source_url",
    "source_priority",
)


def build_provenance(
    *,
    ticker: str,
    source_id: str,
    source_priority: int,
    document_hash: str | None,
    source_url: str | None = None,
    company_name: str | None = None,
    filing_type: str | None = None,
    reporting_period: str | None = None,
    filing_date: str | None = None,
    original_filename: str | None = None,
    mime_type: str | None = None,
    company_id: str | None = None,
    alternate_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    t = ticker.upper().strip()
    return {
        "company_id": company_id or f"nse:{t}",
        "company_name": company_name,
        "source": source_id,
        "filing_type": filing_type,
        "reporting_period": reporting_period,
        "filing_date": filing_date,
        "document_hash": document_hash,
        "download_timestamp": now_iso(),
        "original_filename": original_filename,
        "mime_type": mime_type,
        "source_url": source_url,
        "source_priority": int(source_priority),
        "alternate_sources": list(alternate_sources or []),
    }


def _prov_path(document_hash: str) -> Path:
    root = ensure_dirs() / "collection" / "provenance"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{document_hash}.json"


def persist_provenance(document_hash: str, provenance: dict[str, Any]) -> Path:
    path = _prov_path(document_hash)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        alts = list(existing.get("alternate_sources") or [])
        # Record additional discovery sources without discarding prior provenance
        new_alt = {
            "source": provenance.get("source"),
            "source_url": provenance.get("source_url"),
            "source_priority": provenance.get("source_priority"),
            "filing_date": provenance.get("filing_date"),
            "reporting_period": provenance.get("reporting_period"),
            "recorded_at": now_iso(),
        }
        # Avoid exact duplicate alternate entries
        key = (new_alt.get("source"), new_alt.get("source_url"))
        have = {(a.get("source"), a.get("source_url")) for a in alts}
        if key not in have and new_alt.get("source") != existing.get("source"):
            alts.append(new_alt)
        for a in provenance.get("alternate_sources") or []:
            k = (a.get("source"), a.get("source_url"))
            if k not in have:
                alts.append(a)
                have.add(k)
        existing["alternate_sources"] = alts
        existing["last_seen_at"] = now_iso()
        write_json_atomic(path, existing)
        return path
    payload = dict(provenance)
    payload["immutable_primary"] = True
    payload["created_at"] = now_iso()
    write_json_atomic(path, payload)
    return path


def load_provenance(document_hash: str) -> dict[str, Any] | None:
    path = _prov_path(document_hash)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def record_duplicate_provenance(
    *,
    document_hash: str,
    source_id: str,
    source_url: str | None,
    source_priority: int,
    reporting_period: str | None = None,
    filing_date: str | None = None,
) -> dict[str, Any]:
    """When the same filing arrives from another source, keep one blob + all sources."""
    existing = load_provenance(document_hash) or {
        "document_hash": document_hash,
        "alternate_sources": [],
    }
    alts = list(existing.get("alternate_sources") or [])
    entry = {
        "source": source_id,
        "source_url": source_url,
        "source_priority": source_priority,
        "reporting_period": reporting_period,
        "filing_date": filing_date,
        "recorded_at": now_iso(),
        "duplicate_detected": True,
    }
    key = (entry["source"], entry["source_url"])
    have = {(a.get("source"), a.get("source_url")) for a in alts}
    if key not in have and (existing.get("source"), existing.get("source_url")) != key:
        alts.append(entry)
    existing["alternate_sources"] = alts
    existing["last_duplicate_at"] = now_iso()
    path = _prov_path(document_hash)
    write_json_atomic(path, existing)
    return existing
