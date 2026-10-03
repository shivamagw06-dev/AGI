"""Raw Evidence Layer — immutable original filings + checksums."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from financial_statements_engine.store import ensure_dirs, paths_for
from financial_statements_engine.util import now_iso, write_json_atomic


def content_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def evidence_id_for(data: bytes) -> str:
    return f"sha256:{content_sha256(data)}"


def store_raw(
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
    ext: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist immutable raw bytes + metadata. Idempotent on content hash.

    ``extra`` merges additive provenance fields (FSE-02.3) without changing
    the immutable byte blob contract.
    """
    ensure_dirs()
    digest = content_sha256(data)
    eid = f"sha256:{digest}"
    t = ticker.upper().strip()
    p = paths_for(t)
    p["raw"].mkdir(parents=True, exist_ok=True)
    p["raw_meta"].mkdir(parents=True, exist_ok=True)
    suffix = ext or ("xbrl" if document_type == "xbrl" else document_type)
    blob_path = p["raw"] / f"{digest}.{suffix}"
    meta_path = p["raw_meta"] / f"{digest}.json"

    if not blob_path.exists():
        blob_path.write_bytes(data)
    elif blob_path.read_bytes() != data:
        raise ValueError(f"raw evidence collision for {eid}: bytes differ")

    meta = {
        "evidence_id": eid,
        "ticker": t,
        "entity": entity or t,
        "source": source,
        "source_url": source_url,
        "document_type": document_type,
        "period_type": period_type,
        "period_end": period_end,
        "fiscal_year": fiscal_year,
        "fiscal_period": fiscal_period,
        "retrieved_at": now_iso(),
        "content_sha256": digest,
        "bytes_path": str(blob_path),
        "immutable": True,
        "lifecycle": "raw_verified",
    }
    if extra:
        # Do not allow extra to clobber content identity fields
        for k, v in extra.items():
            if k in {"evidence_id", "content_sha256", "bytes_path", "immutable"}:
                continue
            meta[k] = v
    if not meta_path.exists():
        write_json_atomic(meta_path, meta)
    return meta


def load_raw_meta(ticker: str, evidence_id: str) -> dict[str, Any] | None:
    digest = evidence_id.removeprefix("sha256:")
    path = paths_for(ticker.upper().strip())["raw_meta"] / f"{digest}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_raw_bytes(ticker: str, evidence_id: str) -> bytes | None:
    meta = load_raw_meta(ticker, evidence_id)
    if not meta:
        return None
    path = Path(str(meta["bytes_path"]))
    if not path.exists():
        return None
    return path.read_bytes()
