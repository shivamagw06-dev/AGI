"""KIP service facade — institutional knowledge APIs (P0 + P1)."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

from app.core.config import get_settings
from app.kip.bulk import expand_bulk_items
from app.kip.client_search import client_search
from app.kip.flags import KipFlags
from app.kip.graph import link_prediction, view_for_entity
from app.kip.house_view import build_house_view, build_research_history
from app.kip.models import (
    BulkIngestRequest,
    BulkIngestResult,
    ClientSearchRequest,
    ClientSearchResponse,
    CompanyDossier,
    CompanyKnowledge,
    DocumentType,
    HouseView,
    IngestRequest,
    KipDocument,
    PredictionEvalRequest,
    PredictionRecord,
    PredictionStats,
    RagEvidencePack,
    ResearchHistory,
    ResearchTimeline,
    SearchResponse,
    ThemeKnowledge,
)
from app.kip.pipeline import KipPipeline
from app.kip.predictions import compute_stats, evaluate_prediction, extract_predictions_from_document
from app.kip.rag import research_writer_context
from app.kip.search import search, similar_documents
from app.kip.sources import (
    normalize_agi_request,
    normalize_broker_request,
    normalize_internal_request,
    normalize_newsletter_request,
)
from app.kip.store import KipStore
from app.kip import persist as kip_persist


class KipService:
    """Knowledge Intelligence Platform — permanent institutional memory of AGI."""

    def __init__(
        self,
        store: KipStore | None = None,
        flags: KipFlags | None = None,
        *,
        embedding_dim: int | None = None,
        load_snapshot: bool = True,
    ) -> None:
        settings = get_settings()
        self.flags = flags or KipFlags.from_settings(settings)
        self.store = store or KipStore()
        self.embedding_dim = embedding_dim if embedding_dim is not None else 256
        self.pipeline = KipPipeline(self.store, self.flags, embedding_dim=self.embedding_dim)
        self._persist_meta: dict[str, Any] = {"loaded": False}
        # Snapshot writes serialise the entire store in one json.dumps. At
        # ~2k documents and ~37k chunks that is a large, wholly synchronous
        # operation, so it is coalesced rather than run per ingest.
        self._save_lock = threading.Lock()
        self._last_save_at: float = 0.0
        self._pending_saves: int = 0
        self._save_min_interval = float(os.environ.get("KIP_SNAPSHOT_MIN_INTERVAL_SECONDS", "300"))
        self._save_max_pending = int(os.environ.get("KIP_SNAPSHOT_MAX_PENDING_INGESTS", "25"))
        if load_snapshot:
            try:
                self._persist_meta = kip_persist.load_store(self.store)
            except Exception as exc:
                self._persist_meta = {"ok": False, "loaded": False, "error": str(exc)[:200]}

    def ingest(self, request: IngestRequest) -> KipDocument:
        self._require_enabled()
        doc = self.pipeline.ingest(request)
        self._post_ingest(doc)
        return doc

    def ingest_agi(self, request: IngestRequest) -> KipDocument:
        self._require_enabled()
        if not self.flags.kip_auto_ingest:
            raise RuntimeError("KIP_AUTO_INGEST is disabled")
        return self.ingest(normalize_agi_request(request))

    def ingest_broker(self, request: IngestRequest | BulkIngestRequest) -> KipDocument | BulkIngestResult:
        self._require_enabled()
        if not self.flags.kip_auto_ingest:
            raise RuntimeError("KIP_AUTO_INGEST is disabled")
        if isinstance(request, BulkIngestRequest):
            return self.ingest_bulk(request.model_copy(update={"source_channel": "broker"}))
        return self.ingest(normalize_broker_request(request))

    def ingest_newsletter(self, request: IngestRequest | BulkIngestRequest) -> KipDocument | BulkIngestResult:
        self._require_enabled()
        if not self.flags.kip_auto_ingest:
            raise RuntimeError("KIP_AUTO_INGEST is disabled")
        if isinstance(request, BulkIngestRequest):
            return self.ingest_bulk(request.model_copy(update={"source_channel": "newsletter"}))
        return self.ingest(normalize_newsletter_request(request))

    def ingest_internal(self, request: IngestRequest) -> KipDocument:
        self._require_enabled()
        if not self.flags.kip_auto_ingest:
            raise RuntimeError("KIP_AUTO_INGEST is disabled")
        return self.ingest(normalize_internal_request(request))

    def ingest_bulk(self, request: BulkIngestRequest) -> BulkIngestResult:
        self._require_enabled()
        if not self.flags.kip_auto_ingest:
            raise RuntimeError("KIP_AUTO_INGEST is disabled")
        reqs = expand_bulk_items(
            request.items,
            zip_base64=request.zip_base64,
            default_broker=request.default_broker,
            source_channel=request.source_channel,
        )
        ingested: list[str] = []
        failed: list[dict[str, str]] = []
        for req in reqs:
            try:
                if request.source_channel == "newsletter":
                    req = normalize_newsletter_request(req)
                elif request.source_channel == "internal":
                    req = normalize_internal_request(req)
                elif request.source_channel == "agi":
                    req = normalize_agi_request(req)
                else:
                    req = normalize_broker_request(req)
                doc = self.ingest(req)
                ingested.append(doc.document_id)
            except Exception as exc:
                failed.append({"title": req.title, "error": str(exc)})
        return BulkIngestResult(ingested=ingested, failed=failed, count=len(ingested))

    def get_document(self, document_id: str) -> KipDocument | None:
        self._require_enabled()
        return self.store.get_document(document_id)

    def retire_article(self, article_id: str) -> KipDocument | None:
        """Tombstone an unpublished CMS article without deleting immutable history."""
        self._require_enabled()
        doc = self.store.retire_article(article_id)
        if doc is not None:
            try:
                kip_persist.save_store(self.store)
            except Exception:
                pass
        return doc

    def get_company(self, ticker: str) -> CompanyKnowledge:
        self._require_enabled()
        t = ticker.upper()
        doc_ids = self.store.company_document_ids(t)
        docs = [self.store.get_document(i) for i in doc_ids]
        docs = [d for d in docs if d is not None]
        themes: list[str] = []
        sectors: list[str] = []
        related: list[str] = []
        bull: list[str] = []
        bear: list[str] = []
        risks: list[str] = []
        catalysts: list[str] = []
        latest_thesis = ""
        latest_date = None
        for d in docs:
            for x in d.investment.themes:
                if x not in themes:
                    themes.append(x)
            for x in d.investment.sectors:
                if x not in sectors:
                    sectors.append(x)
            for x in d.investment.tickers:
                if x.upper() != t and x not in related:
                    related.append(x)
            bull.extend(d.research.bull_case)
            bear.extend(d.research.bear_case)
            risks.extend(d.research.risks)
            catalysts.extend(d.research.catalysts)
            if d.research.investment_thesis and (
                latest_date is None or (d.document.date and d.document.date >= latest_date)
            ):
                latest_thesis = d.research.investment_thesis
                latest_date = d.document.date
        timeline = None
        if self.flags.kip_timeline:
            timeline = ResearchTimeline(ticker=t, events=self.store.get_timeline(t))
        graph = None
        if self.flags.kip_graph:
            graph = view_for_entity(t, nodes=self.store.nodes, edges=self.store.edges)
        return CompanyKnowledge(
            ticker=t,
            documents=doc_ids,
            themes=themes,
            sectors=sectors,
            related_companies=related,
            latest_thesis=latest_thesis,
            bull_case=_uniq(bull)[:20],
            bear_case=_uniq(bear)[:20],
            risks=_uniq(risks)[:20],
            catalysts=_uniq(catalysts)[:20],
            timeline=timeline,
            graph=graph,
        )

    def get_theme(self, theme_id: str) -> ThemeKnowledge:
        self._require_enabled()
        key = theme_id.lower()
        doc_ids = self.store.theme_document_ids(key)
        tickers: list[str] = []
        related_themes: list[str] = []
        for i in doc_ids:
            d = self.store.get_document(i)
            if d is None:
                continue
            for t in d.investment.tickers:
                if t not in tickers:
                    tickers.append(t)
            for th in d.investment.themes:
                if th.lower() != key and th not in related_themes:
                    related_themes.append(th)
        return ThemeKnowledge(
            theme_id=key,
            theme=theme_id,
            documents=doc_ids,
            tickers=tickers,
            related_themes=related_themes,
        )

    def house_view(self, ticker: str) -> HouseView:
        self._require_enabled()
        if not self.flags.kip_house_view:
            raise RuntimeError("KIP_HOUSE_VIEW is disabled")
        t = ticker.upper()
        docs = [self.store.get_document(i) for i in self.store.company_document_ids(t)]
        docs = [d for d in docs if d is not None]
        return build_house_view(t, docs, predictions=self.store.list_predictions(t))

    def research_history(self, ticker: str) -> ResearchHistory:
        self._require_enabled()
        t = ticker.upper()
        docs = [self.store.get_document(i) for i in self.store.company_document_ids(t)]
        docs = [d for d in docs if d is not None]
        timeline = None
        if self.flags.kip_timeline:
            timeline = ResearchTimeline(ticker=t, events=self.store.get_timeline(t))
        return build_research_history(t, docs, timeline=timeline)

    def predictions(self, ticker: str) -> list[PredictionRecord]:
        self._require_enabled()
        if not self.flags.kip_prediction_tracking:
            raise RuntimeError("KIP_PREDICTION_TRACKING is disabled")
        return self.store.list_predictions(ticker)

    def prediction_stats(self, ticker: str | None = None) -> PredictionStats:
        self._require_enabled()
        if not self.flags.kip_prediction_tracking:
            raise RuntimeError("KIP_PREDICTION_TRACKING is disabled")
        return compute_stats(self.store.list_predictions(ticker), ticker=ticker)

    def evaluate_prediction(self, req: PredictionEvalRequest) -> PredictionRecord:
        self._require_enabled()
        if not self.flags.kip_prediction_tracking:
            raise RuntimeError("KIP_PREDICTION_TRACKING is disabled")
        pred = self.store.get_prediction(req.prediction_id)
        if pred is None:
            raise KeyError(f"prediction not found: {req.prediction_id}")
        updated = evaluate_prediction(pred, req)
        self.store.put_prediction(updated)
        if self.flags.kip_graph:
            link_prediction(
                updated.prediction_id,
                updated.ticker,
                updated.document_id,
                nodes=self.store.nodes,
                edges=self.store.edges,
                outcome=updated.hit,
            )
        return updated

    def company_dossier(self, ticker: str) -> CompanyDossier:
        self._require_enabled()
        t = ticker.upper()
        house = self.house_view(t) if self.flags.kip_house_view else None
        history = self.research_history(t)
        preds = self.store.list_predictions(t) if self.flags.kip_prediction_tracking else []
        stats = compute_stats(preds, ticker=t) if self.flags.kip_prediction_tracking else None
        timeline = ResearchTimeline(ticker=t, events=self.store.get_timeline(t)) if self.flags.kip_timeline else None
        graph = view_for_entity(t, nodes=self.store.nodes, edges=self.store.edges) if self.flags.kip_graph else None
        return CompanyDossier(
            ticker=t,
            house_view=house,
            research_history=history,
            predictions=preds,
            prediction_stats=stats,
            timeline=timeline,
            graph=graph,
        )

    def search(
        self,
        query: str,
        *,
        mode: str = "hybrid",
        limit: int = 10,
        ticker: str | None = None,
        sector: str | None = None,
        theme: str | None = None,
        broker: str | None = None,
    ) -> SearchResponse:
        self._require_enabled()
        return search(
            query,
            documents=self.store.documents,
            chunks=self.store.chunks,
            mode=mode,
            limit=limit,
            ticker=ticker,
            sector=sector,
            theme=theme,
            broker=broker,
            dim=self.embedding_dim,
        )

    def timeline(self, ticker: str) -> ResearchTimeline:
        self._require_enabled()
        if not self.flags.kip_timeline:
            raise RuntimeError("KIP_TIMELINE is disabled")
        return ResearchTimeline(ticker=ticker.upper(), events=self.store.get_timeline(ticker))

    def similar(self, document_id: str, *, limit: int = 10) -> SearchResponse:
        self._require_enabled()
        return similar_documents(
            document_id,
            documents=self.store.documents,
            chunks=self.store.chunks,
            limit=limit,
        )

    def graph(self, entity: str):
        self._require_enabled()
        if not self.flags.kip_graph:
            raise RuntimeError("KIP_GRAPH is disabled")
        return view_for_entity(entity, nodes=self.store.nodes, edges=self.store.edges)

    def rag(
        self,
        query: str,
        *,
        ticker: str | None = None,
        limit: int = 8,
        engine_states: list[dict[str, Any]] | None = None,
        l4_opinion: dict[str, Any] | None = None,
        portfolio_exposure: dict[str, Any] | None = None,
    ) -> RagEvidencePack:
        self._require_enabled()
        if not self.flags.kip_rag:
            raise RuntimeError("KIP_RAG is disabled")
        from app.kip.rag import build_priority_evidence_pack

        return build_priority_evidence_pack(
            query,
            documents=self.store.documents,
            chunks=self.store.chunks,
            ticker=ticker,
            limit=limit,
            dim=self.embedding_dim,
            engine_states=engine_states,
            l4_opinion=l4_opinion,
            portfolio_exposure=portfolio_exposure,
        )

    def client_search(self, req: ClientSearchRequest) -> ClientSearchResponse:
        self._require_enabled()
        if not self.flags.kip_rag:
            raise RuntimeError("KIP_RAG is disabled")
        return client_search(
            req,
            documents=self.store.documents,
            chunks=self.store.chunks,
            predictions=self.store.list_predictions(req.ticker) if req.ticker else self.store.list_predictions(),
            dim=self.embedding_dim,
        )

    def research_context(
        self,
        query: str,
        *,
        ticker: str | None = None,
        engine_states: list[dict[str, Any]] | None = None,
        l4_opinion: dict[str, Any] | None = None,
        portfolio_exposure: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_enabled()
        if not self.flags.kip_rag:
            raise RuntimeError("KIP_RAG is disabled")
        return research_writer_context(
            ticker=ticker,
            query=query,
            documents=self.store.documents,
            chunks=self.store.chunks,
            dim=self.embedding_dim,
            engine_states=engine_states,
            l4_opinion=l4_opinion,
            portfolio_exposure=portfolio_exposure,
        )

    def ingest_research_run(self, run: Any) -> KipDocument | None:
        """Self-learning hook: index completed AGI research into institutional memory."""
        if not self.flags.kip or not self.flags.kip_auto_ingest:
            return None
        report = getattr(run, "report", None)
        if report is None:
            return None
        title = getattr(report, "title", None) or f"AGI Research {getattr(run, 'run_id', '')}"
        body_parts = [
            "Investment Thesis",
            getattr(report, "executive_summary", "") or "",
            getattr(run, "cio_thesis", "") or "",
        ]
        for attr, header in (
            ("macro_view", "Macro"),
            ("market_view", "Market"),
            ("sector_view", "Sector"),
            ("company_view", "Company"),
            ("valuation_view", "Valuation"),
        ):
            val = getattr(report, attr, None)
            if val:
                body_parts.append(f"{header}\n{val}")
        findings = getattr(report, "key_findings", None) or []
        if findings:
            body_parts.append("Key Findings\n" + "\n".join(f"- {x}" for x in findings))
        risks = getattr(report, "risks", None) or []
        if risks:
            body_parts.append("Risks\n" + "\n".join(f"- {x}" for x in risks))
        catalysts = getattr(report, "catalysts", None) or []
        if catalysts:
            body_parts.append("Catalysts\n" + "\n".join(f"- {x}" for x in catalysts))
        for case_name in ("bull_case", "bear_case", "base_case"):
            case = getattr(report, case_name, None)
            if case is not None:
                detail = getattr(case, "detail", "") or ""
                label = getattr(case, "label", case_name)
                body_parts.append(f"{case_name.replace('_', ' ').title()}\n- {label}: {detail}")
        content = "\n\n".join(p for p in body_parts if p)
        symbols = list(getattr(run, "symbols", None) or [])
        desk = getattr(getattr(run, "desk", None), "value", None) or str(getattr(run, "desk", "agi"))

        dtype = DocumentType.AGI_RESEARCH
        if "cio" in str(desk).lower():
            dtype = DocumentType.AGI_CIO_REPORT
        elif "brief" in str(desk).lower() or "morning" in str(desk).lower():
            dtype = DocumentType.AGI_DAILY_BRIEF
        elif "portfolio" in str(desk).lower():
            dtype = DocumentType.AGI_MODEL_PORTFOLIO
        req = IngestRequest(
            title=str(title)[:300],
            content=content or str(title),
            author="AGI",
            source="agi",
            document_type=dtype,
            tickers=[str(s).upper() for s in symbols],
            article_id=getattr(run, "run_id", None),
            research_type=dtype.value,
            metadata={"run_id": getattr(run, "run_id", None), "desk": desk},
        )
        return self.ingest_agi(req)

    def health(self) -> dict[str, Any]:
        integrity = kip_persist.integrity_report(self.store, sample_limit=5)
        return {
            "status": "ok" if self.flags.kip else "disabled",
            "platform": "KIP",
            "knowledge_version": "kip-v1.0.1-p1",
            "flags": self.flags.as_dict(),
            "stats": self.store.stats(),
            "persistence": {
                **(integrity.get("persistence") or {}),
                "boot": self._persist_meta,
                "healthy": integrity.get("healthy"),
                "split_brain_risk": integrity.get("split_brain_risk"),
                "vector_chunks": (integrity.get("stats") or {}).get("vector_chunks"),
            },
            "out_of_scope": [
                "model_fine_tuning",
                "model_weight_updates",
                "broker_execution",
                "portfolio_optimisation",
                "research_engine_redesign",
            ],
        }

    def integrity(self, expected_document_ids: list[str] | None = None) -> dict[str, Any]:
        return kip_persist.integrity_report(
            self.store, expected_document_ids=expected_document_ids
        )

    def verify_document(self, document_id: str) -> dict[str, Any]:
        return kip_persist.verify_document_retrievable(self.store, document_id)

    def save_snapshot(self) -> dict[str, Any]:
        """Force a write. Used by the explicit endpoint and at shutdown."""
        with self._save_lock:
            result = kip_persist.save_store(self.store)
            self._last_save_at = time.monotonic()
            self._pending_saves = 0
            return result

    def reload_snapshot(self) -> dict[str, Any]:
        self._persist_meta = kip_persist.load_store(self.store)
        return self._persist_meta

    def _post_ingest(self, doc: KipDocument) -> None:
        if self.flags.kip_prediction_tracking:
            for pred in extract_predictions_from_document(doc):
                self.store.put_prediction(pred)
                if self.flags.kip_graph:
                    link_prediction(
                        pred.prediction_id,
                        pred.ticker,
                        pred.document_id,
                        nodes=self.store.nodes,
                        edges=self.store.edges,
                    )
        self._save_snapshot_debounced()

    def _save_snapshot_debounced(self) -> bool:
        """Coalesce snapshot writes instead of one per ingest.

        save_store() rebuilds the whole store as a single JSON string before
        writing. That was previously called after every successful ingest, so
        as the corpus grew each document cost a full re-serialisation of every
        other document. With the store at ~2k documents / ~37k chunks the
        process spends its time serialising, the uvicorn event loop is starved,
        and /v1/health stops answering while background work carries on — which
        is exactly how the engine presented on 2026-08-19: unresponsive to HTTP
        for hours while still writing snapshots to disk.

        The original comment cited Free-tier restarts, but a durable Render
        disk is mounted now, so losing at most KIP_SNAPSHOT_MIN_INTERVAL_SECONDS
        of ingests to a hard kill is an acceptable trade for a responsive API.
        """
        now = time.monotonic()
        self._pending_saves += 1
        due = (
            self._last_save_at == 0.0
            or self._pending_saves >= self._save_max_pending
            or (now - self._last_save_at) >= self._save_min_interval
        )
        if not due:
            return False
        # Never let two ingests serialise the store concurrently: that doubles
        # peak memory for no benefit, and the second write is redundant.
        if not self._save_lock.acquire(blocking=False):
            return False
        try:
            kip_persist.save_store(self.store)
            self._last_save_at = time.monotonic()
            self._pending_saves = 0
            return True
        except Exception:
            return False
        finally:
            self._save_lock.release()

    def _require_enabled(self) -> None:
        if not self.flags.kip:
            raise RuntimeError("KIP is disabled")


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for i in items:
        key = i.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(i.strip())
    return out
