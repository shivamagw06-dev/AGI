"""IDI pipeline — Document → Collect → Validate → Parse → Object → Evidence Pack."""

from __future__ import annotations

import time
from typing import Any

from knowledge_factory.institutional_documents import store
from knowledge_factory.institutional_documents.chunking import chunk_parsed
from knowledge_factory.institutional_documents.collectors import collect_documents
from knowledge_factory.institutional_documents.evidence import generate_packs
from knowledge_factory.institutional_documents.objects import compile_document_object
from knowledge_factory.institutional_documents.parsers import parse_document
from knowledge_factory.institutional_documents.provenance import assert_chunk_provenance
from knowledge_factory.institutional_documents.schema import FREEZE_LOCKS, IDI_VERSION
from knowledge_factory.institutional_documents.validators import validate_document

PIPELINE_VERSION = "idi-pipeline-v1.0.0"


def ingest_one(raw: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    """Full lifecycle for a single collected document envelope."""
    if not raw.get("ok") or not raw.get("text"):
        return {
            "ok": False,
            "document_id": raw.get("document_id"),
            "reason": raw.get("reason") or "body_unavailable",
            "transparent_insufficiency": True,
            "fabricated": False,
        }

    verdict = validate_document(raw, as_of=as_of)
    raw = {**raw, "validation": verdict, "validator": verdict.get("validator")}
    if not verdict.get("ok"):
        return {
            "ok": False,
            "document_id": raw.get("document_id"),
            "reason": "validation_failed",
            "validation": verdict,
            "fabricated": False,
        }

    try:
        parsed = parse_document(raw)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "document_id": raw.get("document_id"),
            "reason": "parser_failure",
            "error": str(exc)[:200],
            "fabricated": False,
        }

    chunks = chunk_parsed(raw, parsed)
    if not chunks:
        return {
            "ok": False,
            "document_id": raw.get("document_id"),
            "reason": "chunking_empty",
            "fabricated": False,
        }
    if not all(assert_chunk_provenance(c) for c in chunks):
        return {
            "ok": False,
            "document_id": raw.get("document_id"),
            "reason": "missing_provenance",
            "fabricated": False,
        }

    # Persist document without raw giant duplication in list views — keep text for replay
    doc_row = {k: v for k, v in raw.items()}
    doc_row["sections"] = [
        {"section": s["section"], "heading": s["heading"], "page": s["page"]}
        for s in parsed.get("sections") or []
    ]
    doc_row["confidence"] = 0.9
    doc_row["replay_id"] = f"replay_{raw['document_id']}"
    store.put_document(doc_row)
    store.put_chunks(raw["document_id"], chunks)

    obj = compile_document_object(doc_row, parsed, chunks)
    store.put_object(obj["object_id"], obj)
    packs = generate_packs(doc_row, obj, chunks)

    return {
        "ok": True,
        "document_id": raw["document_id"],
        "object_id": obj["object_id"],
        "object_type": obj["object_type"],
        "chunk_count": len(chunks),
        "pack_ids": [p["pack_id"] for p in packs],
        "validation": verdict,
        "fabricated": False,
    }


def run_institutional_documents_pipeline(
    *,
    tickers: list[str] | None = None,
    injected: list[dict[str, Any]] | None = None,
    allow_samples: bool = True,
    as_of: str | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    collected: list[dict[str, Any]] = []
    if injected is not None:
        collected = collect_documents(injected=injected, allow_samples=False)
    elif tickers:
        for t in tickers:
            collected.extend(collect_documents(ticker=t, allow_samples=allow_samples))
    else:
        collected = collect_documents(allow_samples=allow_samples)

    results = []
    ok_n = 0
    for raw in collected:
        res = ingest_one(raw, as_of=as_of)
        results.append(res)
        if res.get("ok"):
            ok_n += 1

    # Soft Research Office publications (knowledge-only)
    ro = _soft_research_office(results)

    quality_failures = []
    for r in results:
        if not r.get("ok"):
            quality_failures.append(r.get("reason") or "failed")
    report = {
        "pipeline_version": PIPELINE_VERSION,
        "idi_version": IDI_VERSION,
        "collected": len(collected),
        "ingested_ok": ok_n,
        "objects_created": ok_n,
        "packs_created": sum(len(r.get("pack_ids") or []) for r in results if r.get("ok")),
        "results": results,
        "validation_failures": store.list_validations(limit=50),
        "research_office_soft": ro,
        "quality_gates": {
            "passed": ok_n > 0 and not any(
                f in {"missing_provenance", "checksum_mismatch", "future_leakage", "duplicate_document", "unknown_source"}
                for f in quality_failures
            ),
            "failures": sorted(set(quality_failures)),
        },
        "runtime_seconds": round(time.perf_counter() - t0, 3),
        "freeze_locks": FREEZE_LOCKS,
        "status": "ok" if ok_n == len(collected) and collected else ("degraded" if ok_n else "error"),
        "reasoning_changed": False,
        "governance_changed": False,
        "knowledge_factory_core_changed": False,
        "fabricated": False,
        "recommendation": None,
    }
    store.record_run(report)
    return report


def _soft_research_office(results: list[dict[str, Any]]) -> dict[str, Any]:
    pubs = []
    for r in results:
        if not r.get("ok"):
            continue
        doc = store.get_document(r["document_id"]) or {}
        pubs.append(
            {
                "publication_type": _pub_type(doc.get("type")),
                "document_id": r["document_id"],
                "company": doc.get("company"),
                "title": doc.get("title"),
                "available_from": doc.get("available_from"),
                "recommendation": None,
            }
        )
    # Change summary — knowledge only
    summary = {
        "new_documents": len(pubs),
        "by_type": {},
        "publications": pubs,
        "recommendation": None,
    }
    for p in pubs:
        summary["by_type"][p["publication_type"]] = summary["by_type"].get(p["publication_type"], 0) + 1
    try:
        from research_office.production import register_external_signal  # type: ignore

        register_external_signal({"source": "IDI", "kind": "DOCUMENT_INGEST", "n": len(pubs)})
        return {"attempted": True, "registered": True, "summary": summary}
    except Exception:
        return {"attempted": True, "registered": False, "summary": summary, "note": "soft_noop"}


def _pub_type(doc_type: str | None) -> str:
    return {
        "ANNUAL_REPORT": "New Annual Report",
        "QUARTERLY_REPORT": "New Quarterly Result",
        "INVESTOR_PRESENTATION": "New Presentation",
        "CONFERENCE_CALL_TRANSCRIPT": "New Transcript",
        "CORPORATE_GOVERNANCE_REPORT": "New Governance Filing",
        "EXCHANGE_FILING": "New Governance Filing",
    }.get(str(doc_type or ""), "Document Change Summary")
