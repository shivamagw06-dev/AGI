"""FRE end-to-end pipeline — acquire → parse → chunk → embed → index → evidence → graph."""

from __future__ import annotations

import time
from typing import Any

from app.fre.acquisition import seed_documents, soft_acquire_from_aoi
from app.fre.chunking import chunk_document
from app.fre.evidence import cross_validate, extract_evidence
from app.fre.graph import update_graph
from app.fre.index import embed_chunk, hybrid_search
from app.fre.models import FreDocument
from app.fre.parser import parse_document
from app.fre.planner import plan_retrieval
from app.fre.rerank import rerank
from app.fre.router import route_plan
from app.fre.store import FreStore
from app.fre.understanding import understand_query


class FrePipeline:
    def __init__(
        self,
        store: FreStore,
        *,
        aoi: Any | None = None,
        kip: Any | None = None,
        faa: Any | None = None,
    ) -> None:
        self.store = store
        self.aoi = aoi
        self.kip = kip
        self.faa = faa
        self._seeded = False

    def ensure_seed(self) -> dict[str, Any]:
        if self._seeded and self.store.documents:
            return {"seeded": True, "documents": len(self.store.documents)}
        docs = seed_documents()
        result = self.ingest_documents(docs)
        self._seeded = True
        return result

    def ingest_documents(self, documents: list[FreDocument], *, publish_kip: bool = False) -> dict[str, Any]:
        ingested = []
        failed = 0
        total_chunks = 0
        t0 = time.perf_counter()
        for doc in documents:
            try:
                stored = self.store.put_document(doc)
                parsed = parse_document(stored)
                chunks = chunk_document(stored, parsed)
                for ch in chunks:
                    embed_chunk(ch)
                total_chunks += self.store.put_chunks(chunks)
                ingested.append(stored.document_id)
                if publish_kip and self.kip is not None:
                    self._soft_publish_kip(stored, chunks)
            except Exception as exc:
                failed += 1
                self.store.metrics.documents_failed += 1
                self.store.metrics.parse_failures += 1
                self.store.audit_event("ingest_failed", error=str(exc)[:160], title=doc.title)
        # evidence bootstrap from all chunks via self-query on title keywords
        self.store.record_latency(embed_ms=(time.perf_counter() - t0) * 1000 / max(1, len(documents)))
        return {
            "ingested": ingested,
            "failed": failed,
            "chunks": total_chunks,
            "snapshot": self.store.snapshot(),
        }

    def ingest_query_sources(self, query: str, *, publish_kip: bool = False) -> dict[str, Any]:
        """Soft-acquire AOI hits for a query and ingest."""
        docs = soft_acquire_from_aoi(self.aoi, query=query, limit=8)
        if not docs:
            return {"ingested": [], "failed": 0, "chunks": 0, "note": "no_aoi_docs"}
        return self.ingest_documents(docs, publish_kip=publish_kip)

    def run_query(
        self,
        query: str,
        *,
        limit: int = 20,
        company: str | None = None,
        document_type: str | None = None,
        min_authority: int | None = None,
        acquire: bool = True,
        update_kg: bool = True,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        self.ensure_seed()
        understanding = understand_query(query, aoi=self.aoi)
        plan = plan_retrieval(query, aoi=self.aoi, understanding=understanding)
        routes = route_plan(plan)

        acquisition: dict[str, Any] = {}
        # Prefer FAA (live acquisition) over legacy AOI soft-ingest.
        if acquire and self.faa is not None:
            try:
                acquisition = self.faa.acquire(query, limit=24) or {}
            except Exception as exc:
                acquisition = {"error": str(exc)[:160], "programme": "FAA"}
        elif acquire and self.aoi is not None:
            try:
                self.ingest_query_sources(query)
                acquisition = {"mode": "aoi_soft", "programme": "AOI"}
            except Exception:
                acquisition = {}

        company_filter = company or understanding.primary_entity
        hits = hybrid_search(
            self.store,
            query,
            limit=100,
            company=company_filter if company else None,
            document_type=document_type,
            min_authority=min_authority,
        )
        top = rerank(query, hits, top_k=max(limit, 20))
        evidence = extract_evidence(top, limit=limit)
        evidence = cross_validate(self.store, evidence)

        graph = {}
        if update_kg:
            docs = [self.store.documents[h["document_id"]] for h in top if h.get("document_id") in self.store.documents]
            # unique docs
            uniq = {d.document_id: d for d in docs}
            graph = update_graph(self.store, documents=list(uniq.values()), evidence=evidence)

        related_docs = []
        seen = set()
        for h in top:
            did = h.get("document_id")
            if did in seen or did not in self.store.documents:
                continue
            seen.add(did)
            related_docs.append(self.store.documents[did].to_dict())

        ms = (time.perf_counter() - t0) * 1000
        self.store.record_latency(retrieval_ms=ms)

        return {
            "programme": "FRE",
            "architecture_status": "v1.0.1 LOCKED",
            "does_not_answer": True,
            "query": query,
            "understanding": understanding.to_dict(),
            "plan": plan.to_dict(),
            "routes": routes,
            "acquisition": {
                "programme": acquisition.get("programme") or ("FAA" if self.faa else None),
                "live_fetch": acquisition.get("live_fetch"),
                "discovered": acquisition.get("discovered"),
                "fetched": acquisition.get("fetched"),
                "skipped_cached": acquisition.get("skipped_cached"),
                "indexed_to_fre": acquisition.get("indexed_to_fre"),
                "errors": acquisition.get("errors") or [],
            },
            "top_evidence": [e.to_dict() for e in evidence[:limit]],
            "top_sources": related_docs[:12],
            "chunks": top[:limit],
            "metadata": {
                "company_filter": company_filter,
                "document_type": document_type,
                "min_authority": min_authority,
                "retrieval_ms": round(ms, 2),
                "faa_bound": self.faa is not None,
            },
            "confidence": {
                "mean_evidence_confidence": round(
                    sum(e.confidence for e in evidence) / max(1, len(evidence)), 4
                ),
                "conflicts": sum(1 for e in evidence if e.validation_status == "conflict"),
                "corroborated": sum(1 for e in evidence if e.validation_status == "corroborated"),
            },
            "knowledge_graph": {
                "links": (graph.get("edges") or [])[:40],
                "nodes": (graph.get("nodes") or [])[:40],
            },
            "related_documents": related_docs[:12],
        }

    def _soft_publish_kip(self, doc: FreDocument, chunks: list) -> None:
        try:
            text = "\n\n".join(ch.text for ch in chunks[:8])
            payload = {
                "title": doc.title,
                "text": text or doc.raw_text,
                "source": doc.source,
                "document_type": doc.document_type,
                "url": doc.url,
                "company": doc.company,
                "symbol": doc.symbol,
                "published_at": doc.published_at,
                "metadata": {"fre_document_id": doc.document_id, "authority": doc.authority},
            }
            if hasattr(self.kip, "ingest_text"):
                self.kip.ingest_text(payload)
            elif hasattr(self.kip, "ingest"):
                self.kip.ingest(payload)
        except Exception:
            self.store.audit_event("kip_publish_soft_fail", document_id=doc.document_id)
