"""Continuous learning writeback — extract → memories → graph → deltas.

Called after every successful document ingest / Gather learn. Soft — never raises.
"""

from __future__ import annotations

from typing import Any

from institutional_knowledge_layer.deltas import detect_deltas, persist_deltas
from institutional_knowledge_layer.extractor import extract_knowledge
from institutional_knowledge_layer.flags import ikl_writeback_enabled
from institutional_knowledge_layer.graph import upsert_relationships
from institutional_knowledge_layer.memory.company import merge_company_extraction
from institutional_knowledge_layer.memory.industry import merge_industry_extraction
from institutional_knowledge_layer.memory.macro import detect_macro_topics, merge_macro_extraction
from institutional_knowledge_layer.schema import IKL_CODE, IKL_VERSION, now_ts
from institutional_knowledge_layer import store


def _doc_fields(doc: Any) -> dict[str, Any]:
    if isinstance(doc, dict):
        d = doc
    else:
        try:
            d = doc.model_dump(mode="json") if hasattr(doc, "model_dump") else dict(doc or {})
        except Exception:
            d = {}
    text = (
        d.get("text")
        or d.get("content")
        or d.get("body")
        or d.get("markdown")
        or d.get("summary")
        or ""
    )
    title = d.get("title") or d.get("name") or d.get("headline") or ""
    source_id = str(
        d.get("document_id") or d.get("id") or d.get("source_id") or d.get("uid") or ""
    )
    source_type = str(
        d.get("source_channel")
        or d.get("doc_type")
        or d.get("source_type")
        or d.get("channel")
        or "unknown"
    )
    company_hint = None
    for key in ("ticker", "company", "entity", "primary_ticker"):
        if d.get(key):
            company_hint = str(d[key]).upper()
            break
    meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
    if not company_hint and isinstance(d.get("tickers"), list) and d["tickers"]:
        company_hint = str(d["tickers"][0]).upper()
    return {
        "text": str(text)[:120_000],
        "title": str(title)[:400],
        "source_id": source_id or None,
        "source_type": source_type,
        "company_hint": company_hint,
        "industry_hint": d.get("industry") or d.get("sector") or meta.get("industry"),
        "meta": {
            **meta,
            "tickers": d.get("tickers") or meta.get("tickers"),
            "themes": d.get("themes") or meta.get("themes"),
            "sectors": d.get("sectors") or meta.get("sectors"),
        },
    }


def learn_from_document(doc: Any) -> dict[str, Any]:
    """Universal writeback for one ingested document."""
    if not ikl_writeback_enabled():
        return {"ok": False, "skipped": True, "reason": "ikl_writeback_disabled"}
    try:
        fields = _doc_fields(doc)
        if not (fields["text"] or fields["title"]):
            return {"ok": False, "skipped": True, "reason": "empty_document"}

        extraction = extract_knowledge(
            text=fields["text"],
            title=fields["title"],
            source_id=fields["source_id"] or "",
            source_type=fields["source_type"],
            company_hint=fields["company_hint"],
            industry_hint=str(fields["industry_hint"] or "") or None,
            meta=fields["meta"],
        )
        store.append_jsonl(
            "extractions",
            {
                "source_id": extraction.get("source_id"),
                "confidence": extraction.get("confidence"),
                "companies": (extraction.get("slots") or {}).get("companies"),
                "at": now_ts(),
            },
        )

        bag = extraction.get("slots") or {}
        companies = [str(c).upper() for c in (bag.get("companies") or []) if c][:8]
        if fields["company_hint"] and fields["company_hint"] not in companies:
            companies = [fields["company_hint"]] + companies

        company_updates = []
        for ticker in companies[:5]:
            # prior extraction for delta (best-effort last extraction for ticker)
            prior = None
            try:
                prev_mem = store.load_memory("company", ticker)
                # reconstruct a thin prior bag from memory slots
                if prev_mem:
                    ps = prev_mem.get("slots") or {}
                    prior = {
                        "slots": {
                            "guidance": ps.get("latest_guidance") or [],
                            "risks": ps.get("key_risks") or [],
                            "management": ps.get("management_timeline") or [],
                            "financial_kpis": ps.get("historical_kpis") or [],
                            "events": [],
                        }
                    }
            except Exception:
                prior = None
            company_updates.append(merge_company_extraction(ticker, extraction, source_id=fields["source_id"]))
            deltas = detect_deltas(ticker=ticker, extraction=extraction, prior_extraction=prior)
            if deltas:
                persist_deltas(deltas)

        industry_updates = []
        for ind in (bag.get("industries") or [])[:5]:
            industry_updates.append(
                merge_industry_extraction(str(ind), extraction, source_id=fields["source_id"])
            )

        macro_updates = []
        topics = detect_macro_topics(f"{fields['title']}\n{fields['text'][:4000]}")
        for topic in topics[:5]:
            macro_updates.append(
                merge_macro_extraction(
                    topic,
                    extraction,
                    source_id=fields["source_id"],
                    affected_industries=[str(x) for x in (bag.get("industries") or [])[:6]],
                )
            )

        graph = upsert_relationships(
            bag.get("relationships") or [],
            source_id=fields["source_id"],
        )

        result = {
            "ok": True,
            "engine": IKL_CODE,
            "version": IKL_VERSION,
            "source_id": fields["source_id"],
            "extraction_confidence": extraction.get("confidence"),
            "companies_updated": [u.get("ticker") for u in company_updates if u.get("ok")],
            "industries_updated": [u.get("industry") for u in industry_updates if u.get("ok")],
            "macro_updated": [u.get("topic") for u in macro_updates if u.get("ok")],
            "graph": graph,
            "at": now_ts(),
        }
        store.append_jsonl("writebacks", result)
        return result
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "soft": True}


def learn_from_cgl_run(cgl_run: dict[str, Any] | None) -> dict[str, Any]:
    """Soft-wire after Continuous Gather → Learn cycle."""
    if not ikl_writeback_enabled():
        return {"ok": False, "skipped": True}
    try:
        run = dict(cgl_run or {})
        docs = []
        for key in ("documents", "ingested", "learnings", "archived_learnings"):
            if isinstance(run.get(key), list):
                docs.extend(run[key])
        # Also learn from archived learnings store if present on run summary
        results = []
        for doc in docs[:40]:
            results.append(learn_from_document(doc))
        # If no docs, still stamp cycle
        summary = {
            "ok": True,
            "engine": IKL_CODE,
            "cgl_run_id": run.get("run_id"),
            "documents_processed": len(results),
            "ok_n": sum(1 for r in results if r.get("ok")),
            "at": now_ts(),
        }
        store.append_jsonl("cgl_writebacks", summary)
        return {**summary, "results": results[:20]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "soft": True}
