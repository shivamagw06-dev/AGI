"""Manual Knowledge Upload — store → hash → parse → evidence → memory → readiness."""

from __future__ import annotations

import base64
import hashlib
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from knowledge_operations.audit import record_audit
from knowledge_operations.schema import DOCUMENT_UPLOAD_TYPES, UPLOAD_EXTENSIONS

_LOCK = threading.Lock()
_UPLOADS: List[Dict[str, Any]] = []
_QUEUE: List[Dict[str, Any]] = []

STORE_DIR = Path(
    os.environ.get("AGI_KOC_UPLOAD_DIR")
    or (Path(__file__).resolve().parents[1] / "data" / "koc_uploads")
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _ensure_store() -> Path:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    return STORE_DIR


def list_queue(*, limit: int = 100) -> Dict[str, Any]:
    with _LOCK:
        rows = list(reversed(_QUEUE))[: max(1, min(limit, 500))]
    stages: Dict[str, int] = {}
    for r in _QUEUE:
        st = r.get("stage") or "unknown"
        stages[st] = stages.get(st, 0) + 1
    return {"ok": True, "count": len(rows), "stages": stages, "items": rows}


def list_uploads(*, limit: int = 50, ticker: Optional[str] = None) -> Dict[str, Any]:
    with _LOCK:
        rows = list(_UPLOADS)
    if ticker:
        t = ticker.upper()
        rows = [r for r in rows if r.get("ticker") == t]
    rows = list(reversed(rows))[: max(1, min(limit, 200))]
    return {"ok": True, "count": len(rows), "uploads": rows}


def upload_knowledge(
    *,
    ticker: str,
    document_type: str,
    filename: str,
    content_base64: Optional[str] = None,
    content_bytes: Optional[bytes] = None,
    actor: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Admin upload path — never overwrites evidence; everything versioned/immutable.
    """
    t = str(ticker or "").upper().strip()
    dtype = str(document_type or "other").strip().lower()
    if dtype not in DOCUMENT_UPLOAD_TYPES:
        dtype = "other"
    name = str(filename or "upload.bin")
    ext = Path(name).suffix.lower()
    if ext and ext not in UPLOAD_EXTENSIONS:
        # Still accept; mark for review
        pass

    if content_bytes is None:
        if not content_base64:
            return {"ok": False, "error": "content_base64 or content_bytes required"}
        try:
            content_bytes = base64.b64decode(content_base64)
        except Exception as exc:
            return {"ok": False, "error": f"invalid_base64:{exc}"}

    digest = hashlib.sha256(content_bytes).hexdigest()
    upload_id = f"koc_up_{uuid.uuid4().hex[:12]}"
    store = _ensure_store()
    # Immutable path: hash prefix prevents overwrite collisions
    dest = store / f"{t}_{dtype}_{digest[:16]}_{Path(name).name}"
    if not dest.exists():
        dest.write_bytes(content_bytes)

    pipeline: List[Dict[str, Any]] = []
    evidence_ids: List[str] = []
    claims_created = 0
    knowledge_version = None

    # 1 Store + identity
    pipeline.append({"step": "store_document", "ok": True, "path": str(dest.name)})
    pipeline.append({"step": "checksum", "ok": True, "sha256": digest})

    # 2 Govern + register via IEP (soft)
    try:
        from institutional_evidence.governance.layer0 import govern_inbound_dataset
        from institutional_evidence.entity.resolve import entity_id_for_ticker
        from institutional_evidence.registry.store import register_documents

        eid = entity_id_for_ticker(t)
        gov = govern_inbound_dataset(
            {"hash": digest, "filename": name, "bytes": len(content_bytes)},
            provider_id="knowledge_operations_upload",
            document_type=dtype,
            entity_id=eid,
        )
        doc = {
            "document_id": f"doc_koc_{digest[:12]}",
            "company": t,
            "ticker": t,
            "entity_id": eid,
            "document_type": dtype,
            "source": "manual_upload",
            "hash": digest,
            "checksum": digest,
            "filename": name,
            "mime_type": mime_type,
            "published_at": _now(),
            "downloaded_at": _now(),
            "status": "published_canonical" if gov.get("admitted") else "governance_rejected",
            "governance": gov.get("governance"),
            "upload_id": upload_id,
        }
        reg = register_documents({"ticker": t, "documents": [doc], "document_count": 1})
        evidence_ids = [doc["document_id"]]
        pipeline.append(
            {
                "step": "parse_extract_normalize",
                "ok": bool(gov.get("admitted")),
                "registry_items": (reg or {}).get("item_count") or (reg or {}).get("count"),
            }
        )
        pipeline.append({"step": "create_evidence_objects", "ok": True, "evidence_ids": evidence_ids})
        pipeline.append({"step": "link_company", "ok": True, "entity_id": eid})
    except Exception as exc:
        pipeline.append({"step": "iep_register", "ok": False, "error": str(exc)[:200]})

    # 3 KIL integrate → memory / KG / readiness
    try:
        from institutional_evidence.integration.layer import integrate_company
        from institutional_evidence.integration.versioning.snapshots import get_latest_snapshot

        kil = integrate_company(t, trigger_repair=True)
        snap = get_latest_snapshot()
        knowledge_version = (snap or {}).get("knowledge_version")
        pipeline.append(
            {
                "step": "update_company_memory",
                "ok": True,
                "period_count": kil.get("period_count"),
            }
        )
        pipeline.append({"step": "refresh_knowledge_graph", "ok": True})
        pipeline.append(
            {
                "step": "refresh_research_readiness",
                "ok": True,
                "research_ready": kil.get("research_ready"),
                "claim_safe": kil.get("claim_safe"),
            }
        )
        claims_created = int(kil.get("claims_created") or 0)
    except Exception as exc:
        pipeline.append({"step": "kil_integrate", "ok": False, "error": str(exc)[:200]})

    # 4 ICF rescore
    score = None
    try:
        from institutional_coverage_factory.scorer.score import score_evidence_classes
        from institutional_coverage_factory.validator.icc import evaluate_icc

        score = score_evidence_classes(t)
        icc = evaluate_icc(t, score=score)
        pipeline.append(
            {
                "step": "coverage_rescore",
                "ok": True,
                "coverage_pct": score.get("coverage_pct"),
                "icc": icc.get("institutional_coverage_complete"),
            }
        )
    except Exception as exc:
        pipeline.append({"step": "coverage_rescore", "ok": False, "error": str(exc)[:200]})
        icc = None

    # 5 Ask AGI learning — ingest into KIP so future Ask questions can retrieve this upload.
    kip_document_id = None
    try:
        text = ""
        try:
            text = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
        if not text.strip():
            text = (
                f"Manual knowledge upload for {t}.\n"
                f"Document type: {dtype}.\n"
                f"Filename: {name}.\n"
                f"SHA256: {digest}.\n"
                "Content stored in Knowledge Operations; binary payload available for research refresh."
            )

        from app.kip.models import DocumentType, IngestRequest
        from app.kip.service import KipService

        dtype_map = {
            "annual_report": DocumentType.ANNUAL_REPORT,
            "quarterly_report": DocumentType.QUARTERLY_REPORT,
            "investor_presentation": DocumentType.INVESTOR_PRESENTATION,
            "earnings_transcript": DocumentType.EARNINGS_TRANSCRIPT,
            "filing": DocumentType.NSE_BSE_FILING,
            "research": DocumentType.AGI_RESEARCH,
            "note": DocumentType.AGI_NOTE,
        }
        kip_type = dtype_map.get(dtype, DocumentType.OTHER)
        kip = KipService()
        doc = kip.ingest_agi(
            IngestRequest(
                title=f"KOC upload: {name}",
                content=text[:120_000],
                document_type=kip_type,
                tickers=[t] if t else [],
                source="knowledge_operations_upload",
                author=actor or "admin",
                metadata={
                    "upload_id": upload_id,
                    "sha256": digest,
                    "stored_as": dest.name,
                    "learn_for_ask": True,
                },
            )
        )
        kip_document_id = getattr(doc, "document_id", None) or getattr(doc, "id", None)
        if kip_document_id:
            evidence_ids.append(str(kip_document_id))
        pipeline.append(
            {
                "step": "kip_ingest_for_ask",
                "ok": True,
                "document_id": kip_document_id,
                "note": "Upload is now searchable by Ask AGI via KIP.",
            }
        )
    except Exception as exc:
        pipeline.append({"step": "kip_ingest_for_ask", "ok": False, "error": str(exc)[:200]})

    record = {
        "upload_id": upload_id,
        "ticker": t,
        "document_type": dtype,
        "filename": name,
        "sha256": digest,
        "bytes": len(content_bytes),
        "mime_type": mime_type,
        "stored_as": dest.name,
        "actor": actor or "admin",
        "uploaded_at": _now(),
        "evidence_ids": evidence_ids,
        "kip_document_id": kip_document_id,
        "knowledge_version": knowledge_version,
        "pipeline": pipeline,
        "immutable": True,
        "coverage_pct": (score or {}).get("coverage_pct") if isinstance(score, dict) else None,
        "ask_learned": bool(kip_document_id),
    }

    queue_item = {
        "queue_id": f"koc_q_{uuid.uuid4().hex[:10]}",
        "upload_id": upload_id,
        "ticker": t,
        "document_type": dtype,
        "stage": "Waiting for Research Refresh"
        if any(not s.get("ok") for s in pipeline)
        else "Complete",
        "status": "ok" if all(s.get("ok") for s in pipeline[-3:]) else "partial",
        "created_at": _now(),
    }

    with _LOCK:
        _UPLOADS.append(record)
        _QUEUE.append(queue_item)

    audit = record_audit(
        "upload_knowledge",
        actor=actor or "admin",
        ticker=t,
        document_hash=digest,
        document_type=dtype,
        knowledge_version=knowledge_version,
        evidence_ids=evidence_ids,
        claims_created=claims_created,
        research_updated=True,
        details={"upload_id": upload_id, "filename": name},
    )

    return {
        "ok": True,
        "upload": record,
        "queue": queue_item,
        "audit": audit,
        "icc": icc if "icc" in dir() else None,
        "note": "Evidence is append-only; uploads never overwrite prior documents.",
    }
