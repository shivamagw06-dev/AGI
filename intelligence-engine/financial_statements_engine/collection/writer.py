"""Raw Evidence Writer — thin façade over FSE-01 raw_evidence (FSE-02 §6.5)."""

from __future__ import annotations

import json
from typing import Any

from financial_statements_engine.collection.sources import logical_key
from financial_statements_engine.raw_evidence import content_sha256, load_raw_meta, store_raw
from financial_statements_engine.store import ensure_dirs, paths_for
from financial_statements_engine.util import now_iso, write_json_atomic


def evidence_exists(content_digest: str) -> bool:
    """True if any ticker already stored this content hash (global index)."""
    root = ensure_dirs()
    idx = root / "collection" / "hash_index.json"
    if not idx.exists():
        return False
    data = json.loads(idx.read_text(encoding="utf-8"))
    return content_digest in (data.get("hashes") or {})


def _index_hash(digest: str, meta: dict[str, Any]) -> None:
    root = ensure_dirs()
    idx_path = root / "collection" / "hash_index.json"
    data: dict[str, Any] = {"hashes": {}}
    if idx_path.exists():
        data = json.loads(idx_path.read_text(encoding="utf-8"))
    hashes = dict(data.get("hashes") or {})
    hashes[digest] = {
        "evidence_id": meta.get("evidence_id"),
        "ticker": meta.get("ticker"),
        "source": meta.get("source"),
        "period_end": meta.get("period_end"),
        "indexed_at": now_iso(),
    }
    data["hashes"] = hashes
    write_json_atomic(idx_path, data)


def prior_for_logical_key(ticker: str, key: str) -> dict[str, Any] | None:
    path = paths_for(ticker)["raw_meta"].parent.parent / "collection" / "logical_index.json"
    # store under collection/
    root = ensure_dirs()
    path = root / "collection" / "logical_index.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return (data.get("keys") or {}).get(key)


def _index_logical(key: str, meta: dict[str, Any]) -> None:
    root = ensure_dirs()
    path = root / "collection" / "logical_index.json"
    data: dict[str, Any] = {"keys": {}}
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    keys = dict(data.get("keys") or {})
    keys[key] = {
        "evidence_id": meta.get("evidence_id"),
        "content_sha256": meta.get("content_sha256"),
        "ticker": meta.get("ticker"),
        "source": meta.get("source"),
        "document_type": meta.get("document_type"),
        "period_end": meta.get("period_end"),
        "indexed_at": now_iso(),
    }
    data["keys"] = keys
    write_json_atomic(path, data)


def write_evidence(
    *,
    ticker: str,
    data: bytes,
    source: str,
    source_url: str | None = None,
    document_type: str = "xbrl",
    period_type: str | None = None,
    period_end: str | None = None,
    fiscal_year: int | None = None,
    fiscal_period: str | None = None,
    entity: str | None = None,
    consolidation: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Idempotent raw write. Returns action: stored | duplicate_skipped | restatement_candidate."""
    digest = content_sha256(data)
    lkey = logical_key(
        ticker=ticker,
        period_type=period_type,
        period_end=period_end,
        document_type=document_type,
        consolidation=consolidation,
    )
    prior = prior_for_logical_key(ticker, lkey)

    if evidence_exists(digest):
        existing = load_raw_meta(ticker, f"sha256:{digest}")
        return {
            "action": "duplicate_skipped",
            "evidence_id": f"sha256:{digest}",
            "content_sha256": digest,
            "logical_key": lkey,
            "meta": existing,
            "prior": prior,
        }

    meta = store_raw(
        ticker=ticker,
        data=data,
        source=source,
        source_url=source_url,
        document_type=document_type,
        period_type=period_type,
        period_end=period_end,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        entity=entity,
        extra=extra,
    )
    _index_hash(digest, meta)

    action = "stored"
    prior_evidence_id = None
    if prior and prior.get("content_sha256") and prior.get("content_sha256") != digest:
        action = "restatement_candidate"
        prior_evidence_id = prior.get("evidence_id")
    _index_logical(lkey, meta)

    return {
        "action": action,
        "evidence_id": meta.get("evidence_id"),
        "content_sha256": digest,
        "logical_key": lkey,
        "meta": meta,
        "prior_evidence_id": prior_evidence_id,
    }
