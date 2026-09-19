"""FRE service facade — evidence serving API (does not answer users)."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.fre.acquisition import acquire_from_text
from app.fre.flags import FreFlags
from app.fre.graph import graph_for_entity
from app.fre.pipeline import FrePipeline
from app.fre.scheduler import FreScheduler
from app.fre.store import FreStore


class FreService:
    """Finance Retrieval Engine — acquisition + evidence serving only."""

    def __init__(
        self,
        *,
        flags: FreFlags | None = None,
        store: FreStore | None = None,
        aoi: Any | None = None,
        kip: Any | None = None,
        eve: Any | None = None,
        faa: Any | None = None,
    ) -> None:
        self.flags = flags or FreFlags.from_settings(get_settings())
        self.store = store or FreStore()
        self.aoi = aoi
        self.kip = kip
        self.eve = eve
        self.faa = faa
        self.pipeline = FrePipeline(self.store, aoi=aoi, kip=kip, faa=faa)
        self.scheduler = FreScheduler()
        if self.flags.fre:
            self.pipeline.ensure_seed()

    def bind(self, **engines: Any) -> None:
        for name, eng in engines.items():
            if hasattr(self, name):
                setattr(self, name, eng)
        self.pipeline.aoi = self.aoi
        self.pipeline.kip = self.kip
        self.pipeline.faa = self.faa

    def _require(self) -> None:
        if not self.flags.fre:
            raise RuntimeError("FRE disabled")

    def health(self) -> dict[str, Any]:
        snap = self.store.snapshot() if self.flags.fre else {}
        return {
            "status": "ok" if self.flags.fre else "disabled",
            "layer": "Finance Retrieval Engine",
            "programme": "FRE",
            "version": "fre-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "after_faa_before_cae_reasoning",
            "does_not_answer": True,
            "upstream": ["faa"],
            "faa_bound": self.faa is not None,
            "no_redesign": ["faa", "aoi", "eve", "kf", "kc", "kip", "cae", "irp", "rsp", "ask_agi"],
            "pipeline": [
                "intent_detection",
                "entity_detection",
                "query_planning",
                "source_routing",
                "document_acquisition",
                "parse_clean_chunk",
                "embed_hybrid_search",
                "rerank",
                "evidence_extract_validate",
                "knowledge_graph_update",
                "serve_evidence",
            ],
            "invariants": [
                "never_answer_user",
                "evidence_requires_provenance",
                "prefer_authoritative_sources",
                "dedupe_by_checksum",
                "version_documents",
                "flag_contradictions",
            ],
            "flags": self.flags.as_dict(),
            "snapshot": snap,
            "metrics": self.store.metrics.model_dump(),
            "scheduler": self.scheduler.status() if self.flags.fre_scheduler else {},
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        self.pipeline.ensure_seed()
        docs = sorted(self.store.documents.values(), key=lambda d: d.retrieved_at, reverse=True)
        evidence = sorted(self.store.evidence.values(), key=lambda e: e.created_at, reverse=True)
        return {
            "programme": "FRE",
            "architecture_status": "v1.0.1 LOCKED",
            "does_not_answer": True,
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
            "recent_documents": [d.to_dict() for d in docs[:30]],
            "recent_evidence": [e.to_dict() for e in evidence[:30]],
            "authority_mix": self._authority_mix(),
            "scheduler": self.scheduler.status(),
            "audit": self.store.audit[-30:],
        }

    def query(self, q: str, *, limit: int = 20, company: str | None = None) -> dict[str, Any]:
        """Primary evidence pack API — FRE never answers."""
        self._require()
        return self.pipeline.run_query(
            q,
            limit=limit,
            company=company,
            acquire=self.flags.fre_acquisition,
            update_kg=self.flags.fre_graph,
        )

    def search(
        self,
        q: str,
        *,
        limit: int = 20,
        company: str | None = None,
        document_type: str | None = None,
        min_authority: int | None = None,
    ) -> dict[str, Any]:
        self._require()
        pack = self.pipeline.run_query(
            q,
            limit=limit,
            company=company,
            document_type=document_type,
            min_authority=min_authority,
            acquire=False,
            update_kg=False,
        )
        return {
            "programme": "FRE",
            "architecture_status": "v1.0.1 LOCKED",
            "query": q,
            "hits": pack.get("chunks") or [],
            "evidence": pack.get("top_evidence") or [],
            "understanding": pack.get("understanding") or {},
            "confidence": pack.get("confidence") or {},
        }

    def company(self, key: str, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        self.pipeline.ensure_seed()
        docs = self.store.documents_for_company(key)
        evidence = self.store.evidence_for_company(key)
        if not evidence:
            pack = self.query(key, limit=limit, company=key)
            evidence_dicts = pack.get("top_evidence") or []
            graph = pack.get("knowledge_graph") or {}
        else:
            evidence_dicts = [e.to_dict() for e in evidence[:limit]]
            graph = graph_for_entity(self.store, key)
        return {
            "programme": "FRE",
            "architecture_status": "v1.0.1 LOCKED",
            "company": key,
            "documents": [d.to_dict() for d in docs[:40]],
            "evidence": evidence_dicts,
            "timeline": sorted(
                [
                    {
                        "date": d.published_at,
                        "title": d.title,
                        "document_type": d.document_type,
                        "source": d.source,
                        "url": d.url,
                    }
                    for d in docs
                    if d.published_at
                ],
                key=lambda x: x["date"] or "",
                reverse=True,
            )[:40],
            "knowledge_graph": graph,
        }

    def document(self, document_id: str) -> dict[str, Any]:
        self._require()
        doc = self.store.documents.get(document_id)
        if not doc:
            raise RuntimeError("document_not_found")
        chunks = [c.to_dict() for c in self.store.chunks.values() if c.document_id == document_id]
        evidence = [e.to_dict() for e in self.store.evidence.values() if e.document_id == document_id]
        return {
            "programme": "FRE",
            "document": doc.to_dict(),
            "chunks": chunks,
            "evidence": evidence,
        }

    def evidence(self, *, company: str | None = None, limit: int = 40) -> dict[str, Any]:
        self._require()
        items = list(self.store.evidence.values())
        if company:
            c = company.lower()
            items = [e for e in items if c in (e.company or "").lower() or c == (e.symbol or "").lower()]
        items = sorted(items, key=lambda e: e.confidence, reverse=True)[:limit]
        return {
            "programme": "FRE",
            "count": len(items),
            "evidence": [e.to_dict() for e in items],
        }

    def timeline(self, *, company: str | None = None, limit: int = 40) -> dict[str, Any]:
        self._require()
        docs = list(self.store.documents.values())
        if company:
            docs = self.store.documents_for_company(company)
        rows = sorted(
            [
                {
                    "date": d.published_at,
                    "title": d.title,
                    "document_type": d.document_type,
                    "source": d.source,
                    "company": d.company,
                    "symbol": d.symbol,
                    "url": d.url,
                    "authority": d.authority,
                }
                for d in docs
            ],
            key=lambda x: x.get("date") or "",
            reverse=True,
        )[:limit]
        return {"programme": "FRE", "timeline": rows}

    def news(self, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        docs = [
            d
            for d in self.store.documents.values()
            if (d.document_type or "").lower() in {"news", "press"} or (d.source or "") in {
                "reuters",
                "bloomberg",
                "moneycontrol",
                "economic_times",
                "business_standard",
                "mint",
                "cnbc",
            }
        ]
        docs = sorted(docs, key=lambda d: d.published_at or "", reverse=True)[:limit]
        return {"programme": "FRE", "news": [d.to_dict() for d in docs]}

    def graph(self, *, entity: str | None = None) -> dict[str, Any]:
        self._require()
        if entity:
            return {"programme": "FRE", **graph_for_entity(self.store, entity)}
        return {
            "programme": "FRE",
            "nodes": [n.to_dict() for n in list(self.store.nodes.values())[:100]],
            "edges": [e.to_dict() for e in list(self.store.edges.values())[:200]],
        }

    def ingest(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        payload = payload or {}
        doc = acquire_from_text(
            title=str(payload.get("title") or "Untitled"),
            text=str(payload.get("text") or payload.get("content") or ""),
            url=str(payload.get("url") or ""),
            source=str(payload.get("source") or "general_web"),
            document_type=str(payload.get("document_type") or "unknown"),
            company=payload.get("company"),
            symbol=payload.get("symbol"),
            published_at=payload.get("published_at"),
            organisation=str(payload.get("organisation") or ""),
        )
        result = self.pipeline.ingest_documents(
            [doc],
            publish_kip=bool(self.flags.fre_soft_publish_kip and payload.get("publish_kip", False)),
        )
        stream = str(payload.get("stream") or document_stream(doc.document_type))
        self.scheduler.mark_run(stream, documents=1)
        return result

    def run_jobs(self) -> dict[str, Any]:
        self._require()
        seed = self.pipeline.ensure_seed()
        aoi_docs = 0
        if self.aoi is not None and self.flags.fre_acquisition:
            try:
                res = self.pipeline.ingest_query_sources("India markets filings news macro", publish_kip=False)
                aoi_docs = len(res.get("ingested") or [])
            except Exception:
                aoi_docs = 0
        self.scheduler.mark_run("company_filings", documents=aoi_docs, note="soft_aoi_cycle")
        self.scheduler.mark_run("news", documents=0, note="cadence_registered")
        return {
            "programme": "FRE",
            "seed": seed,
            "aoi_documents": aoi_docs,
            "scheduler": self.scheduler.status(),
            "snapshot": self.store.snapshot(),
        }

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Ask AGI / CAE soft retrieval — evidence only, never a recommendation.

        Architecture rule: Ask never calls ``faa.acquire``. This path reads the
        seeded/indexed corpus (and snapshots filled by the FAA background
        collector). Use ``POST /v1/faa/acquire`` or the background collector for
        live crawls — never the Ask request path.
        """
        self._require()
        if not self.flags.fre_ask_agi:
            return {"programme": "FRE", "disabled": True, "hits": []}
        # Seed corpus if empty — never FAA/Playwright on Ask.
        try:
            self.pipeline.ensure_seed()
        except Exception:
            pass
        pack = self.pipeline.run_query(
            query,
            limit=limit,
            acquire=False,
            update_kg=False,
        )
        return {
            "programme": "FRE",
            "architecture_status": "v1.0.1 LOCKED",
            "does_not_answer": True,
            "query": query,
            "acquisition_mode": "index_only",
            "live_faa_acquire": False,
            "understanding": pack.get("understanding"),
            "plan_tasks": [t.get("description") for t in (pack.get("plan") or {}).get("tasks", [])][:12],
            "hits": [
                {
                    "label": e.get("claim"),
                    "score": e.get("confidence"),
                    "source": e.get("source"),
                    "document_type": e.get("document_type"),
                    "section": e.get("section"),
                    "page": e.get("page"),
                    "company": e.get("company"),
                    "validation_status": e.get("validation_status"),
                    "published_at": e.get("published_at"),
                    "evidence_id": e.get("evidence_id"),
                }
                for e in (pack.get("top_evidence") or [])[:limit]
            ],
            "top_sources": [
                {
                    "title": d.get("title"),
                    "document_type": d.get("document_type"),
                    "source": d.get("source"),
                    "authority": d.get("authority"),
                    "url": d.get("url"),
                    "published_at": d.get("published_at"),
                }
                for d in (pack.get("top_sources") or [])[:8]
            ],
            "confidence": pack.get("confidence"),
            "knowledge_graph": pack.get("knowledge_graph"),
            "invariants": [
                "never_answer_user",
                "evidence_requires_provenance",
                "never_faa_acquire_on_ask",
            ],
        }

    def _authority_mix(self) -> dict[str, int]:
        mix: dict[str, int] = {}
        for d in self.store.documents.values():
            mix[d.document_type] = mix.get(d.document_type, 0) + 1
        return mix


def document_stream(document_type: str | None) -> str:
    dt = (document_type or "").lower()
    if "news" in dt:
        return "news"
    if "annual" in dt:
        return "annual_reports"
    if "quarter" in dt:
        return "quarterly_reports"
    if dt in {"rbi", "sebi", "government", "pib"}:
        return "government"
    if "filing" in dt:
        return "company_filings"
    return "general"
